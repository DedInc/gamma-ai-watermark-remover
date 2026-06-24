"""Upload validation and processor dispatch helpers for the web app."""

import asyncio
import logging
import os
import tempfile
import uuid
from typing import Any

from fastapi import UploadFile
from werkzeug.utils import secure_filename

from utils.file_helpers import allowed_file, get_file_extension
from utils.processors import (
    KeynoteProcessor,
    PDFProcessor,
    PNGProcessor,
    PPTXProcessor,
    ZIPProcessor,
)

logger = logging.getLogger(__name__)

INVALID_TYPE_ERROR = (
    "Invalid file type. Supported: PDF, PPTX, Keynote (.key), ZIP of PNGs."
)

PROCESSORS = {
    "pdf": PDFProcessor(),
    "pptx": PPTXProcessor(),
    "key": KeynoteProcessor(),
    "zip": ZIPProcessor(),
    "png": PNGProcessor(),
}


def normalize_upload_name(original_name: str) -> tuple[str, str, str | None]:
    """Return sanitized filename, extension, and validation error if any."""
    if not original_name:
        return "Unknown", "", "No file selected."
    if not allowed_file(original_name):
        return original_name, "", INVALID_TYPE_ERROR

    original_extension = get_file_extension(original_name)
    filename = secure_filename(original_name)
    if not get_file_extension(filename) and original_extension:
        filename = f"{uuid.uuid4().hex[:8]}.{original_extension}"

    extension = get_file_extension(filename)
    if not extension:
        return original_name, "", "Invalid file name. Extension missing."
    return filename, extension, None


async def process_form_upload(
    uploaded_file: UploadFile, output_folder: str
) -> dict[str, Any]:
    """Process one upload for the HTML form and return template context."""
    filename, extension, error = normalize_upload_name(uploaded_file.filename or "")
    if error:
        return {"error_message": _form_error_message(error)}

    logger.info(
        "Processing file: %s (original: %s, type: %s)",
        filename,
        uploaded_file.filename,
        extension,
    )

    try:
        result, output_filename = await _process_upload(
            uploaded_file, output_folder, filename, extension, unique_output=False
        )
        if not result["success"]:
            return {"error_message": result.get("error", "Unknown error occurred.")}
        return _template_context(result, output_filename, extension)
    except Exception as exc:
        logger.error("Error processing file: %s", exc)
        return {"error_message": f"Error processing file: {exc}"}


async def process_api_upload(
    uploaded_file: UploadFile, output_folder: str
) -> dict[str, Any]:
    """Process one upload for the batch API and return a JSON-safe result."""
    original_name = uploaded_file.filename or "Unknown"
    filename, extension, error = normalize_upload_name(uploaded_file.filename or "")
    if error:
        return {"filename": original_name, "success": False, "error": error}

    try:
        result, output_filename = await _process_upload(
            uploaded_file, output_folder, filename, extension, unique_output=True
        )
        if not result["success"]:
            return {
                "filename": original_name,
                "success": False,
                "error": result.get("error", "Unknown error occurred."),
            }
        return _api_success_result(result, output_filename, original_name, extension)
    except Exception as exc:
        logger.error("Error processing %s: %s", original_name, exc)
        return {"filename": original_name, "success": False, "error": str(exc)}


async def _process_upload(
    uploaded_file: UploadFile,
    output_folder: str,
    filename: str,
    extension: str,
    unique_output: bool,
) -> tuple[dict[str, Any], str]:
    """Persist upload temporarily, dispatch it, and always clean up temp input."""
    temp_path = await _write_temp_upload(uploaded_file, extension)
    try:
        output_filename = _output_filename(filename, unique_output)
        output_path = os.path.join(output_folder, output_filename)
        processor = PROCESSORS.get(extension)
        if processor is None:
            return {
                "success": False,
                "error": f"Unsupported file type: {extension}",
            }, ""
        result = await asyncio.to_thread(
            processor.process, temp_path, output_path, filename
        )
        return result, output_filename
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


async def _write_temp_upload(uploaded_file: UploadFile, extension: str) -> str:
    """Write UploadFile content to a temporary file and return its path."""
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=f".{extension}"
    ) as temp_input:
        content = await uploaded_file.read()
        temp_input.write(content)
        temp_input.flush()
        return temp_input.name


def _output_filename(filename: str, unique_output: bool) -> str:
    """Build a processed output filename, optionally avoiding batch collisions."""
    if unique_output:
        return f"processed_{uuid.uuid4().hex[:8]}_{filename}"
    return f"processed_{filename}"


def _template_context(
    result: dict[str, Any], output_filename: str, extension: str
) -> dict[str, Any]:
    """Convert a processor result into template context."""
    context = {"success_message": result["message"]}
    if result.get("has_watermark"):
        context["download_filename"] = output_filename
        context["file_type"] = extension
    return context


def _api_success_result(
    result: dict[str, Any], output_filename: str, original_name: str, extension: str
) -> dict[str, Any]:
    """Convert a processor result into the batch API response shape."""
    has_watermark = result["has_watermark"]
    return {
        "filename": original_name,
        "success": True,
        "has_watermark": has_watermark,
        "message": result["message"],
        "download_filename": output_filename if has_watermark else None,
        "download_url": f"/download/{output_filename}" if has_watermark else None,
        "file_type": extension,
        "stats": result.get("stats"),
    }


def _form_error_message(error: str) -> str:
    """Preserve the friendlier single-upload wording for missing selections."""
    if error == "No file selected.":
        return "No file selected. Please choose a supported file."
    if error == "Invalid file name. Extension missing.":
        return "Invalid file name. Please upload a file with a proper extension."
    return error
