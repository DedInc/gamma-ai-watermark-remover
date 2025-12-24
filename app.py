import os
import tempfile
import logging
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from werkzeug.utils import secure_filename

from utils.file_helpers import allowed_file, get_file_extension
from utils.processors import PDFProcessor, PPTXProcessor

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create necessary directories
UPLOAD_FOLDER = "uploads"
OUTPUT_FOLDER = "outputs"

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = FastAPI(title="Gamma AI Watermark Remover", version="2.3.0")

templates = Jinja2Templates(directory="templates")

# Initialize processors
pdf_processor = PDFProcessor()
pptx_processor = PPTXProcessor()


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
            {
                "request": request,
                "error_message": "No file selected. Please choose a PDF or PPTX file.",
            },
        )

    if not allowed_file(pdf_file.filename):
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error_message": "Invalid file type. Please upload a PDF or PowerPoint (.pptx) file.",
            },
        )

    # Extract extension before secure_filename to handle Unicode filenames
    original_extension = get_file_extension(pdf_file.filename)
    filename = secure_filename(pdf_file.filename)

    # If secure_filename stripped the extension (e.g., Cyrillic names), restore it
    if not get_file_extension(filename) and original_extension:
        # Generate a safe filename with preserved extension
        import uuid

        filename = f"{uuid.uuid4().hex[:8]}.{original_extension}"

    file_extension = get_file_extension(filename)

    logger.info(
        f"Processing file: {filename} (original: {pdf_file.filename}, type: {file_extension})"
    )

    # Additional validation: ensure we have a valid extension
    if not file_extension:
        return templates.TemplateResponse(
            "index.html",
            {
                "request": request,
                "error_message": "Invalid file name. Please upload a file with a proper extension (.pdf or .pptx).",
            },
        )

    # Create temp file with appropriate extension
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f".{file_extension}"
    ) as temp_input:
        upload_path = temp_input.name

        try:
            content = await pdf_file.read()
            temp_input.write(content)
            temp_input.flush()

            # Dispatch to appropriate handler based on file type
            if file_extension == "pdf":
                return await _process_pdf(request, upload_path, filename)
            elif file_extension == "pptx":
                return await _process_pptx(request, upload_path, filename)
            else:
                return templates.TemplateResponse(
                    "index.html",
                    {
                        "request": request,
                        "error_message": f"Unsupported file type: {file_extension}",
                    },
                )

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return templates.TemplateResponse(
                "index.html",
                {
                    "request": request,
                    "error_message": f"Error processing file: {str(e)}",
                },
            )

        finally:
            try:
                os.unlink(upload_path)
            except Exception:
                pass


async def _process_pdf(request: Request, upload_path: str, filename: str):
    """Process a PDF file for watermark removal."""
    output_filename = f"processed_{filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    result = pdf_processor.process(upload_path, output_path, filename)

    if not result["success"]:
        raise Exception(result["error"])

    template_data = {"request": request, "success_message": result["message"]}

    if result["has_watermark"]:
        template_data["download_filename"] = output_filename
        template_data["file_type"] = "pdf"

    return templates.TemplateResponse("index.html", template_data)


async def _process_pptx(request: Request, upload_path: str, filename: str):
    """Process a PPTX file for watermark removal."""
    output_filename = f"processed_{filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)

    result = pptx_processor.process(upload_path, output_path, filename)

    if not result["success"]:
        raise Exception(result["error"])

    template_data = {"request": request, "success_message": result["message"]}

    if result["has_watermark"]:
        template_data["download_filename"] = output_filename
        template_data["file_type"] = "pptx"

    return templates.TemplateResponse("index.html", template_data)


# ===========================
# DOWNLOAD ENDPOINT
# ===========================
@app.get("/download/{filename}")
async def download_processed_file(filename: str):
    from fastapi.responses import FileResponse

    file_path = os.path.join(OUTPUT_FOLDER, filename)

    if not os.path.exists(file_path):
        return {"error": "File not found."}

    # Determine MIME type based on file extension
    from utils.file_helpers import get_mime_type

    file_extension = get_file_extension(filename)
    mime_type = get_mime_type(file_extension)

    return FileResponse(file_path, media_type=mime_type, filename=filename)


# ===========================
# ERROR HANDLERS
# ===========================
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error_message": "Page not found."},
            status_code=404,
        )
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "error_message": f"Server error: {exc.detail}"},
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "error_message": f"Internal server error: {str(exc)}"},
        status_code=500,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=8999)
