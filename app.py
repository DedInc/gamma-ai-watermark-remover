import os
import tempfile
import logging
import uuid
import asyncio
import time
from contextlib import asynccontextmanager
from typing import List
import io
import zipfile
from fastapi import FastAPI, File, UploadFile, Request, Query
from fastapi.responses import HTMLResponse, FileResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException
from werkzeug.utils import secure_filename

from utils.file_helpers import allowed_file, get_file_extension, get_mime_type
from utils.processors import PDFProcessor, PPTXProcessor, KeynoteProcessor, ZIPProcessor, PNGProcessor

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

# Auto-cleanup interval (seconds) and max file age (seconds)
CLEANUP_INTERVAL = 600  # Run cleanup every 10 minutes
MAX_FILE_AGE = 3600  # Delete files older than 1 hour


async def _cleanup_old_files():
    """Background task that periodically deletes files in outputs/ older than 1 hour."""
    while True:
        try:
            now = time.time()
            cleaned = 0
            for filename in os.listdir(OUTPUT_FOLDER):
                if filename == ".gitkeep":
                    continue
                file_path = os.path.join(OUTPUT_FOLDER, filename)
                if os.path.isfile(file_path):
                    file_age = now - os.path.getmtime(file_path)
                    if file_age > MAX_FILE_AGE:
                        os.unlink(file_path)
                        cleaned += 1
                        logger.debug(f"Auto-cleanup: removed {filename} (age: {file_age:.0f}s)")
            if cleaned > 0:
                logger.info(f"Auto-cleanup: removed {cleaned} expired file(s) from {OUTPUT_FOLDER}/")
        except Exception as e:
            logger.error(f"Auto-cleanup error: {e}")
        await asyncio.sleep(CLEANUP_INTERVAL)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown tasks."""
    cleanup_task = asyncio.create_task(_cleanup_old_files())
    logger.info("Auto-cleanup background task started (interval: %ds, max age: %ds)", CLEANUP_INTERVAL, MAX_FILE_AGE)
    yield
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        pass
    logger.info("Auto-cleanup background task stopped")


app = FastAPI(title="Gamma AI Watermark Remover", version="2.5.0", lifespan=lifespan)

templates = Jinja2Templates(directory="templates")

# Initialize processors
pdf_processor     = PDFProcessor()
pptx_processor    = PPTXProcessor()
keynote_processor = KeynoteProcessor()
zip_processor     = ZIPProcessor()
png_processor     = PNGProcessor()


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.5.0"}


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/remove_watermark")
async def remove_watermark(request: Request, pdf_file: UploadFile = File(...)):
    """
    Remove watermarks from PDF, PPTX, Keynote, or ZIP (PNG slides) files.
    The parameter is named 'pdf_file' for backward compatibility with the form.
    """
    if not pdf_file.filename:
        return templates.TemplateResponse(
            request, "index.html",
            {"error_message": "No file selected. Please choose a supported file."},
        )

    if not allowed_file(pdf_file.filename):
        return templates.TemplateResponse(
            request, "index.html",
            {"error_message": "Invalid file type. Supported: PDF, PPTX, Keynote (.key), ZIP of PNGs."},
        )

    original_extension = get_file_extension(pdf_file.filename)
    filename = secure_filename(pdf_file.filename)

    if not get_file_extension(filename) and original_extension:
        filename = f"{uuid.uuid4().hex[:8]}.{original_extension}"

    file_extension = get_file_extension(filename)

    logger.info(f"Processing file: {filename} (original: {pdf_file.filename}, type: {file_extension})")

    if not file_extension:
        return templates.TemplateResponse(
            request, "index.html",
            {"error_message": "Invalid file name. Please upload a file with a proper extension."},
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_input:
        upload_path = temp_input.name
        try:
            content = await pdf_file.read()
            temp_input.write(content)
            temp_input.flush()

            if file_extension == "pdf":
                return await _process_pdf(request, upload_path, filename)
            elif file_extension == "pptx":
                return await _process_pptx(request, upload_path, filename)
            elif file_extension == "key":
                return await _process_keynote(request, upload_path, filename)
            elif file_extension == "zip":
                return await _process_zip(request, upload_path, filename)
            elif file_extension == "png":
                return await _process_png(request, upload_path, filename)
            else:
                return templates.TemplateResponse(
                    request, "index.html",
                    {"error_message": f"Unsupported file type: {file_extension}"},
                )

        except Exception as e:
            logger.error(f"Error processing file: {str(e)}")
            return templates.TemplateResponse(
                request, "index.html",
                {"error_message": f"Error processing file: {str(e)}"},
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
    result = await asyncio.to_thread(pdf_processor.process, upload_path, output_path, filename)
    if not result["success"]:
        raise Exception(result["error"])
    context = {"success_message": result["message"]}
    if result["has_watermark"]:
        context["download_filename"] = output_filename
        context["file_type"] = "pdf"
    return templates.TemplateResponse(request, "index.html", context)


async def _process_pptx(request: Request, upload_path: str, filename: str):
    """Process a PPTX file for watermark removal."""
    output_filename = f"processed_{filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    result = await asyncio.to_thread(pptx_processor.process, upload_path, output_path, filename)
    if not result["success"]:
        raise Exception(result["error"])
    context = {"success_message": result["message"]}
    if result["has_watermark"]:
        context["download_filename"] = output_filename
        context["file_type"] = "pptx"
    return templates.TemplateResponse(request, "index.html", context)


async def _process_keynote(request: Request, upload_path: str, filename: str):
    """Process a Keynote file for watermark removal."""
    output_filename = f"processed_{filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    result = await asyncio.to_thread(keynote_processor.process, upload_path, output_path, filename)
    if not result["success"]:
        raise Exception(result["error"])
    context = {"success_message": result["message"]}
    if result.get("has_watermark"):
        context["download_filename"] = output_filename
        context["file_type"] = "key"
    return templates.TemplateResponse(request, "index.html", context)


async def _process_zip(request: Request, upload_path: str, filename: str):
    """Process a ZIP of PNG slides for watermark removal."""
    output_filename = f"processed_{filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    result = await asyncio.to_thread(zip_processor.process, upload_path, output_path, filename)
    if not result["success"]:
        raise Exception(result["error"])
    context = {"success_message": result["message"]}
    if result.get("has_watermark"):
        context["download_filename"] = output_filename
        context["file_type"] = "zip"
    return templates.TemplateResponse(request, "index.html", context)


async def _process_png(request: Request, upload_path: str, filename: str):
    """Process a single PNG file for watermark removal."""
    output_filename = f"processed_{filename}"
    output_path = os.path.join(OUTPUT_FOLDER, output_filename)
    result = await asyncio.to_thread(png_processor.process, upload_path, output_path, filename)
    if not result["success"]:
        raise Exception(result["error"])
    context = {"success_message": result["message"]}
    if result.get("has_watermark"):
        context["download_filename"] = output_filename
        context["file_type"] = "png"
    return templates.TemplateResponse(request, "index.html", context)


# ===========================
# BATCH API & ZIP DOWNLOAD
# ===========================
@app.post("/api/remove_watermarks")
async def api_remove_watermarks(files: List[UploadFile] = File(...)):
    results = []
    for uploaded_file in files:
        if not uploaded_file.filename:
            results.append({"filename": "Unknown", "success": False, "error": "No file selected."})
            continue

        if not allowed_file(uploaded_file.filename):
            results.append({
                "filename": uploaded_file.filename,
                "success": False,
                "error": "Invalid file type. Supported: PDF, PPTX, Keynote (.key), ZIP of PNGs."
            })
            continue

        original_extension = get_file_extension(uploaded_file.filename)
        filename = secure_filename(uploaded_file.filename)
        if not get_file_extension(filename) and original_extension:
            filename = f"{uuid.uuid4().hex[:8]}.{original_extension}"

        file_extension = get_file_extension(filename)
        if not file_extension:
            results.append({
                "filename": uploaded_file.filename,
                "success": False,
                "error": "Invalid file name. Extension missing."
            })
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=f".{file_extension}") as temp_input:
            upload_path = temp_input.name
            try:
                content = await uploaded_file.read()
                temp_input.write(content)
                temp_input.flush()

                output_filename = f"processed_{filename}"
                output_path = os.path.join(OUTPUT_FOLDER, output_filename)

                if file_extension == "pdf":
                    proc_result = await asyncio.to_thread(pdf_processor.process, upload_path, output_path, filename)
                elif file_extension == "pptx":
                    proc_result = await asyncio.to_thread(pptx_processor.process, upload_path, output_path, filename)
                elif file_extension == "key":
                    proc_result = await asyncio.to_thread(keynote_processor.process, upload_path, output_path, filename)
                elif file_extension == "zip":
                    proc_result = await asyncio.to_thread(zip_processor.process, upload_path, output_path, filename)
                elif file_extension == "png":
                    proc_result = await asyncio.to_thread(png_processor.process, upload_path, output_path, filename)
                else:
                    results.append({
                        "filename": uploaded_file.filename,
                        "success": False,
                        "error": f"Unsupported file type: {file_extension}"
                    })
                    continue

                if not proc_result["success"]:
                    results.append({
                        "filename": uploaded_file.filename,
                        "success": False,
                        "error": proc_result.get("error", "Unknown error occurred.")
                    })
                else:
                    results.append({
                        "filename": uploaded_file.filename,
                        "success": True,
                        "has_watermark": proc_result["has_watermark"],
                        "message": proc_result["message"],
                        "download_filename": output_filename if proc_result["has_watermark"] else None,
                        "download_url": f"/download/{output_filename}" if proc_result["has_watermark"] else None,
                        "file_type": file_extension,
                        "stats": proc_result.get("stats")
                    })
            except Exception as e:
                logger.error(f"Error processing {uploaded_file.filename}: {e}")
                results.append({
                    "filename": uploaded_file.filename,
                    "success": False,
                    "error": str(e)
                })
            finally:
                try:
                    os.unlink(upload_path)
                except Exception:
                    pass
    return {"results": results}


@app.get("/download_zip")
async def download_zip(files: str = Query(...)):
    file_list = [f.strip() for f in files.split(",") if f.strip()]
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename in file_list:
            safe_name = secure_filename(filename)
            file_path = os.path.join(OUTPUT_FOLDER, safe_name)
            if os.path.isfile(file_path):
                zip_file.write(file_path, arcname=safe_name)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=cleaned_files.zip"}
    )


# ===========================
# DOWNLOAD ENDPOINT
# ===========================
@app.get("/download/{filename}")
async def download_processed_file(filename: str):
    file_path = os.path.join(OUTPUT_FOLDER, filename)

    if not os.path.exists(file_path):
        return {"error": "File not found."}

    file_extension = get_file_extension(filename)
    mime_type = get_mime_type(file_extension)

    return FileResponse(file_path, media_type=mime_type, filename=filename)


# ===========================
# ERROR HANDLERS
# ===========================
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(
            request, "index.html", {"error_message": "Page not found."}, status_code=404,
        )
    return templates.TemplateResponse(
        request, "index.html",
        {"error_message": f"Server error: {exc.detail}"},
        status_code=exc.status_code,
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    return templates.TemplateResponse(
        request, "index.html",
        {"error_message": f"Internal server error: {str(exc)}"},
        status_code=500,
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="localhost", port=8999)
