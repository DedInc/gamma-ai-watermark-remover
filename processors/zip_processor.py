"""High-level ZIP/folder PNG watermark processing."""

import logging
import os
import shutil
import tempfile
import zipfile

from processors.png.remover import remove_png_watermark

logger = logging.getLogger(__name__)


class ZIPProcessor:
    """Handles ZIP archives or folders containing PNG slide exports."""

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """Extract, clean PNG files, and write a cleaned ZIP archive."""
        logger.info("Processing ZIP file: %s", filename)
        if not zipfile.is_zipfile(upload_path):
            return {
                "success": False,
                "error": "The uploaded file is not a valid ZIP archive.",
            }

        with tempfile.TemporaryDirectory() as extract_dir:
            self._safe_extract(upload_path, extract_dir)
            return self._process_png_tree(extract_dir, output_path)

    def process_folder(
        self, folder_path: str, output_path: str, folder_name: str
    ) -> dict:
        """Process an already-extracted folder of PNG slides."""
        logger.info("Processing PNG folder: %s", folder_name)
        return self._process_png_tree(folder_path, output_path)

    @staticmethod
    def _safe_extract(zip_path: str, extract_dir: str) -> None:
        """Extract a ZIP archive while skipping path traversal entries."""
        with zipfile.ZipFile(zip_path, "r") as zip_file:
            extract_root = os.path.realpath(extract_dir)
            for member in zip_file.infolist():
                member_path = os.path.realpath(
                    os.path.join(extract_root, member.filename)
                )
                if (
                    member_path.startswith(extract_root + os.sep)
                    or member_path == extract_root
                ):
                    zip_file.extract(member, extract_dir)
                else:
                    logger.warning("Skipping unsafe ZIP entry: %r", member.filename)

    def _process_png_tree(self, root_dir: str, output_zip_path: str) -> dict:
        """Clean all PNG files below root_dir and zip the resulting tree."""
        stats = {"png_total": 0, "png_cleaned": 0, "png_errors": 0}

        with tempfile.TemporaryDirectory() as out_dir:
            for dirpath, _, filenames in os.walk(root_dir):
                self._copy_cleaned_files(root_dir, out_dir, dirpath, filenames, stats)

            if stats["png_total"] == 0:
                return {
                    "success": False,
                    "error": "No PNG files found in the uploaded archive or folder.",
                }

            output_dir = os.path.dirname(output_zip_path)
            if output_dir:
                os.makedirs(output_dir, exist_ok=True)
            self._zip_directory(out_dir, output_zip_path)

        error_note = (
            f" ({stats['png_errors']} failed, originals kept)"
            if stats["png_errors"]
            else ""
        )
        return {
            "success": True,
            "has_watermark": True,
            "message": (
                f"Processing finished! Cleaned {stats['png_cleaned']} of "
                f"{stats['png_total']} PNG slides{error_note}."
            ),
            "stats": stats,
        }

    @staticmethod
    def _copy_cleaned_files(
        root_dir: str, out_dir: str, dirpath: str, filenames: list[str], stats: dict
    ) -> None:
        """Copy files to output tree, cleaning PNG files on the way."""
        rel_dir = os.path.relpath(dirpath, root_dir)
        dest_dir = os.path.join(out_dir, rel_dir) if rel_dir != "." else out_dir
        os.makedirs(dest_dir, exist_ok=True)

        for filename in filenames:
            src = os.path.join(dirpath, filename)
            dst = os.path.join(dest_dir, filename)
            if filename.lower().endswith(".png"):
                stats["png_total"] += 1
                result = remove_png_watermark(src, dst)
                if result["success"]:
                    stats["png_cleaned"] += 1
                else:
                    shutil.copy2(src, dst)
                    stats["png_errors"] += 1
                    logger.warning(
                        "PNG watermark removal failed for '%s': %s",
                        filename,
                        result["error"],
                    )
            else:
                shutil.copy2(src, dst)

    @staticmethod
    def _zip_directory(source_dir: str, output_zip_path: str) -> None:
        """Zip all contents of source_dir into output_zip_path."""
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for dirpath, _, filenames in os.walk(source_dir):
                for filename in filenames:
                    abs_path = os.path.join(dirpath, filename)
                    arc_path = os.path.relpath(abs_path, source_dir)
                    zip_file.write(abs_path, arc_path)
