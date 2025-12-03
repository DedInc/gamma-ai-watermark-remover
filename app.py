import os
import tempfile
from fastapi import FastAPI, File, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from werkzeug.utils import secure_filename

from watermark_detector import WatermarkDetector
from watermark_remover import WatermarkRemover

# Create necessary directories
UPLOAD_FOLDER = 'uploads'
OUTPUT_FOLDER = 'outputs'
ALLOWED_EXTENSIONS = {'pdf'}

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

app = FastAPI(title="Gamma AI Watermark Remover", version="2.2.0")

templates = Jinja2Templates(directory="templates")

detector = WatermarkDetector()
remover = WatermarkRemover()


def allowed_file(filename: str) -> bool:
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/remove_watermark")
async def remove_watermark(request: Request, pdf_file: UploadFile = File(...)):

    if not pdf_file.filename:
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error_message": "No file selected. Please choose a PDF file."}
        )

    if not allowed_file(pdf_file.filename):
        return templates.TemplateResponse(
            "index.html",
            {"request": request, "error_message": "Invalid file type. Please upload a PDF file."}
        )

    filename = secure_filename(pdf_file.filename)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_input:
        upload_path = temp_input.name

        try:
            content = await pdf_file.read()
            temp_input.write(content)
            temp_input.flush()

            print(f"Analyzing file: {filename}")
            elements_to_remove, error = detector.identify_watermarks(upload_path)

            if error:
                raise Exception(error)

            # Case: Watermark exists → process & show download button
            if elements_to_remove:

                output_filename = f"processed_{filename}"
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)

                print("Removing watermarks...")
                images_removed, links_removed = remover.clean_pdf_from_target_domain(upload_path, output_path)

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
                        "download_filename": output_filename
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

        except Exception as e:
            return templates.TemplateResponse(
                "index.html",
                {"request": request, "error_message": f"Error processing file: {str(e)}"}
            )

        finally:
            try:
                os.unlink(upload_path)
            except:
                pass


# ===========================
# NEW DOWNLOAD ENDPOINT
# ===========================
@app.get("/download/{filename}")
async def download_processed_file(filename: str):
    file_path = os.path.join(OUTPUT_FOLDER, filename)

    if not os.path.exists(file_path):
        return {"error": "File not found."}

    return FileResponse(
        file_path,
        media_type="application/pdf",
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
