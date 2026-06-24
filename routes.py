"""HTTP routes for the Gamma watermark remover app."""

from typing import Any

from fastapi import APIRouter, File, Query, Request, UploadFile
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    JSONResponse,
    StreamingResponse,
)
from fastapi.templating import Jinja2Templates

from utils.download_helpers import build_zip, resolve_output_file
from utils.file_helpers import get_file_extension, get_mime_type
from utils.upload_processing import process_api_upload, process_form_upload

APP_VERSION = "2.5.0"
OUTPUT_FOLDER = "outputs"

router = APIRouter()
templates = Jinja2Templates(directory="templates")


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": APP_VERSION}


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> object:
    """Serve the main application page."""
    return templates.TemplateResponse(request, "index.html")


@router.post("/remove_watermark")
async def remove_watermark(
    request: Request, pdf_file: UploadFile = File(...)
) -> object:
    """Remove watermarks from one uploaded file via the HTML form."""
    context = await process_form_upload(pdf_file, OUTPUT_FOLDER)
    return templates.TemplateResponse(request, "index.html", context)


@router.post("/api/remove_watermarks")
async def api_remove_watermarks(
    files: list[UploadFile] = File(...),
) -> dict[str, list[dict[str, Any]]]:
    """Batch endpoint that processes uploaded files sequentially."""
    results = [await process_api_upload(file, OUTPUT_FOLDER) for file in files]
    return {"results": results}


@router.get("/download_zip")
async def download_zip(files: str = Query(...)) -> object:
    """Bundle processed output files into a ZIP download."""
    zip_buffer = build_zip(files, OUTPUT_FOLDER)
    if zip_buffer is None:
        return JSONResponse(
            status_code=400,
            content={
                "error": (
                    "No valid files found to bundle. They may have expired "
                    "or the filenames are invalid."
                )
            },
        )

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=cleaned_files.zip"},
    )


@router.get("/download/{filename}")
async def download_processed_file(filename: str) -> object:
    """Stream a processed output file back to the client."""
    resolved = resolve_output_file(filename, OUTPUT_FOLDER)
    if resolved is None:
        return {"error": "File not found."}

    safe_name, file_path = resolved
    extension = get_file_extension(safe_name)
    return FileResponse(
        file_path, media_type=get_mime_type(extension), filename=safe_name
    )
