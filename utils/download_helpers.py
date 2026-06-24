"""Download helper functions for processed output files."""

import io
import os
import zipfile

from werkzeug.utils import secure_filename


def build_zip(files: str, output_folder: str) -> io.BytesIO | None:
    """Bundle existing output files from a comma-separated filename list."""
    file_list = [file.strip() for file in files.split(",") if file.strip()]
    zip_buffer = io.BytesIO()
    added = 0

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for filename in file_list:
            safe_name = secure_filename(filename)
            file_path = os.path.join(output_folder, safe_name)
            if os.path.isfile(file_path):
                zip_file.write(file_path, arcname=safe_name)
                added += 1

    if added == 0:
        return None
    zip_buffer.seek(0)
    return zip_buffer


def resolve_output_file(filename: str, output_folder: str) -> tuple[str, str] | None:
    """Return safe filename and real path when it exists within output_folder."""
    safe_name = secure_filename(filename)
    if not safe_name:
        return None

    file_path = os.path.realpath(os.path.join(output_folder, safe_name))
    output_root = os.path.realpath(output_folder)
    if not file_path.startswith(output_root + os.sep) or not os.path.isfile(file_path):
        return None
    return safe_name, file_path
