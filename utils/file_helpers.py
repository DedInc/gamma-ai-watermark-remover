"""File handling utility functions."""

ALLOWED_EXTENSIONS = {"pdf", "pptx"}


def allowed_file(filename: str) -> bool:
    """Check if the file extension is allowed."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def get_file_extension(filename: str) -> str:
    """Get the file extension in lowercase."""
    return filename.rsplit(".", 1)[1].lower() if "." in filename else ""


def get_mime_type(extension: str) -> str:
    """Get the MIME type for a file extension."""
    mime_types = {
        "pdf": "application/pdf",
        "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    }
    return mime_types.get(extension, "application/octet-stream")
