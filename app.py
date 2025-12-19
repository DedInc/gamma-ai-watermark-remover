import os
import tempfile
import logging
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from werkzeug.utils import secure_filename

from watermark_detector import WatermarkDetector
from watermark_remover import WatermarkRemover
from pptx_watermark_detector import PPTXWatermarkDetector
from pptx_watermark_remover import PPTXWatermarkRemover

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create necessary directories
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'pdf', 'pptx'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = FastAPI(title="Gamma AI Watermark Remover", version="2.3.0")

templates = Jinja2Templates(directory="templates")

# PDF handlers
pdf_detector = WatermarkDetector()
pdf_remover = WatermarkRemover()

# PPTX handlers
pptx_detector = PPTXWatermarkDetector()
pptx_remover = PPTXWatermarkRemover()


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """Get the file extension in lowercase."""
    return filename.rsplit('.', 1)[1].lower() if '.' in filename else ''


def get_mime_type(extension: str) -> str:
    """Get the MIME type for a file extension."""
    mime_types = {
        'pdf': 'application/pdf',
        'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
    }
    return mime_types.get(extension, 'application/octet-stream')


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/remove_watermark")
async def remove_watermark(request: Request, pdf_file: UploadFile = File(...)):
    """
    Remove watermarks from PDF or PPTX files.
    The parameter is named 'pdf_file' for backward compatibility with the form.
    """
    if not pdf_file.filename:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error_message": "No file selected. Please choose a PDF or PPTX file."}
        )

    if not allowed_file(pdf_file.filename):
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error_message": "Invalid file type. Please upload a PDF or PowerPoint (.pptx) file."}
        )

    filename = secure_filename(pdf_file.filename)
    file_extension = get_file_extension(filename)
    
    logger.info(f"Processing file: {filename} (type: {file_extension})")

    # Create temp file with appropriate extension
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_input:
        upload_path = temp_input.name

        try:
            content = await pdf_file.read()
            temp_input.write(content)
            temp_input.flush()

            # Dispatch to appropriate handler based on file type
            if file_extension == 'pdf':
                return await _process_pdf(request, upload_path, filename)
            elif file_extension == 'pptx':
                return await _process_pptx(request, upload_path, filename)
            else:
                return templates.TemplateResponse(
                    "index.html",
                    {"request": request, "error_message": f"Unsupported file type: {file_extension}"}
                )

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "error_message": f"Error processing file: {str(e)}"}
            )

        finally:
            try:
                os.unlink(upload_path)
            except:
                pass


async def _process_pdf(request: Request, upload_path: str, filename: str):
    """Process a PDF file for watermark removal."""
    logger.info(f"Processing PDF file: {filename}")
    
    elements_to_remove, error = pdf_detector.identify_watermarks(upload_path)

    if error:
        raise Exception(error)

    # Case: Watermark exists → process & show download button
    if elements_to_remove:
        output_filename = f"processed_{filename}"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        logger.info("Removing watermarks from PDF...")
        images_removed, links_removed = pdf_remover.clean_pdf_from_target_domain(upload_path, output_path)

        total_removed = images_removed + links_removed

        success_message = (
            f"Processing finished! Removed {total_removed} elements "
            f"(images: {images_removed}, links: {links_removed})."
        )

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "success_message": success_message,
                "download_filename": output_filename,
                "file_type": "pdf"
            }
        )

    # Case: No watermark found
    else:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "success_message": "Gamma.app watermarks not found in PDF."
            }
        )


async def _process_pptx(request: Request, upload_path: str, filename: str):
    """Process a PPTX file for watermark removal."""
    logger.info(f"Processing PPTX file: {filename}")
    
    # Check for watermarks
    watermark_results = pptx_detector.detect_watermarks(upload_path)
    watermarks_found = [r for r in watermark_results if r['is_watermark']]
    watermark_count = len(watermarks_found)
    
    logger.info(f"Detected {watermark_count} watermarks in PPTX")

    # Case: Watermark exists → process & show download button
    if watermark_count > 0:
        output_filename = f"processed_{filename}"
        output_path = os.path.join(OUTPUT_FOLDER, output_filename)

        logger.info("Removing watermarks from PPTX...")
        result = pptx_remover.remove_watermarks(upload_path, output_path)

        if not result['success']:
            raise Exception(result['error'])

        success_message = (
            f"Processing finished! Removed {result['watermarks_removed']} watermarks "
            f"from {result['layouts_cleaned']} layouts."
        )

        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "success_message": success_message,
                "download_filename": output_filename,
                "file_type": "pptx"
            }
        )

    # Case: No watermark found
    else:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "success_message": "Gamma.app watermarks not found in PowerPoint file."
            }
        )


# ===========================
# DOWNLOAD ENDPOINT
# ===========================
@app.get("/download/{filename}")
async def download_processed_file(filename: str):
    file_path = os.path.join(OUTPUT_FOLDER, filename)

    if not os.path.exists(file_path):
        return {"error": "File not found."}

    # Determine MIME type based on file extension
    file_extension = get_file_extension(filename)
    mime_type = get_mime_type(file_extension)

    return FileResponse(
        file_path,
        media_type=mime_type,
        filename=filename
    )


# ===========================
# ERROR HANDLERS
# ===========================
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error_message": "Page not found."},
            status_code=404
        )
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "error_message": f"Server error: {exc.detail}"},
        status_code=exc.status_code
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "error_message": f"Internal server error: {str(exc)}"},
        status_code=500
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8999)
