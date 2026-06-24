"""Document processing logic for PDF, PPTX, Keynote, and ZIP/PNG files."""

import logging
import os
import shutil
import tempfile
import zipfile

from processors.pdf.detector import WatermarkDetector
from processors.pdf.remover import WatermarkRemover
from processors.pptx.detector import PPTXWatermarkDetector
from processors.pptx.remover import PPTXWatermarkRemover
from processors.png.remover import remove_png_watermark
from processors.keynote.converter import key_to_pptx, pptx_to_key

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF watermark detection and removal."""

    def __init__(self):
        self.detector = WatermarkDetector()
        self.remover = WatermarkRemover()

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """
        Process PDF file for watermark detection and removal.

        Returns dict with 'success', 'message', 'has_watermark', and optionally 'stats'.
        """
        logger.info(f"Processing PDF file: {filename}")

        elements_to_remove, error = self.detector.identify_watermarks(upload_path)

        if error:
            return {"success": False, "error": error}

        if elements_to_remove:
            logger.info("Removing watermarks from PDF...")
            images_removed, links_removed = self.remover.clean_pdf_from_target_domain(
                upload_path, output_path
            )
            total_removed = images_removed + links_removed

            return {
                "success": True,
                "has_watermark": True,
                "message": (
                    f"Processing finished! Removed {total_removed} elements "
                    f"(images: {images_removed}, links: {links_removed})."
                ),
                "stats": {
                    "images_removed": images_removed,
                    "links_removed": links_removed,
                    "total_removed": total_removed,
                },
            }
        else:
            return {
                "success": True,
                "has_watermark": False,
                "message": "Gamma.app watermarks not found in PDF.",
            }


class PPTXProcessor:
    """Handles PPTX watermark detection and removal."""

    def __init__(self):
        self.detector = PPTXWatermarkDetector()
        self.remover = PPTXWatermarkRemover()

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """
        Process PPTX file for watermark detection and removal.

        Returns dict with 'success', 'message', 'has_watermark', and optionally 'stats'.
        """
        logger.info(f"Processing PPTX file: {filename}")

        watermark_results = self.detector.detect_watermarks(upload_path)
        watermarks_found = [r for r in watermark_results if r["is_watermark"]]
        watermark_count = len(watermarks_found)

        logger.info(f"Detected {watermark_count} watermarks in PPTX")

        if watermark_count > 0:
            logger.info("Removing watermarks from PPTX...")
            result = self.remover.remove_watermarks(upload_path, output_path)

            if not result["success"]:
                return {"success": False, "error": result["error"]}

            # slide_count comes from the remover (it already opens the Presentation)
            slide_count = result.get("slide_count", 0)
            slide_info = f" across all {slide_count} slides" if slide_count > 0 else ""
            return {
                "success": True,
                "has_watermark": True,
                "message": (
                    f"Processing finished! Removed {result['watermarks_removed']} watermarks "
                    f"from {result['layouts_cleaned']} slide layouts{slide_info}."
                ),
                "stats": {
                    "watermarks_removed": result["watermarks_removed"],
                    "layouts_cleaned": result["layouts_cleaned"],
                    "slides_cleaned": slide_count,
                },
            }
        else:
            return {
                "success": True,
                "has_watermark": False,
                "message": "Gamma.app watermarks not found in PowerPoint file.",
            }


class KeynoteProcessor:
    """
    Handles .key watermark removal on macOS via Keynote.app.

    Pipeline:
        .key → (Keynote) → .pptx → (PPTXWatermarkRemover) → cleaned .pptx
             → (Keynote) → cleaned .key
    """

    def __init__(self):
        self.pptx_processor = PPTXProcessor()

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """
        Process a Keynote file for watermark removal.

        Returns dict with 'success', 'message', 'has_watermark', and optionally 'stats'.
        """
        logger.info(f"Processing Keynote file: {filename}")

        base = os.path.splitext(filename)[0]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Step 1: Convert .key → .pptx
            tmp_pptx = os.path.join(tmpdir, f"{base}.pptx")
            conv_result = key_to_pptx(upload_path, tmp_pptx)
            if not conv_result["success"]:
                return {"success": False, "error": conv_result["error"]}

            # Step 2: Clean the PPTX
            tmp_cleaned_pptx = os.path.join(tmpdir, f"{base}_cleaned.pptx")
            proc_result = self.pptx_processor.process(tmp_pptx, tmp_cleaned_pptx, f"{base}.pptx")

            if not proc_result["success"]:
                return {"success": False, "error": proc_result.get("error", "PPTX processing failed.")}

            if not proc_result["has_watermark"]:
                # No watermark found — nothing to do
                return {
                    "success": True,
                    "has_watermark": False,
                    "message": "Gamma.app watermarks not found in Keynote presentation.",
                }

            # Step 3: Convert cleaned .pptx → .key
            save_result = pptx_to_key(tmp_cleaned_pptx, output_path)
            if not save_result["success"]:
                return {"success": False, "error": save_result["error"]}

        stats = proc_result.get("stats", {})
        return {
            "success": True,
            "has_watermark": True,
            "message": (
                f"Processing finished! Removed {stats.get('watermarks_removed', '?')} watermarks "
                f"and saved clean Keynote file."
            ),
            "stats": stats,
        }


class ZIPProcessor:
    """
    Handles ZIP archives (or already-extracted folders) containing PNG slide
    images exported from Gamma.app.

    Accepts two upload scenarios:
      • A .zip file   — extracted to a temp dir, PNGs cleaned, re-zipped.
      • A folder      — not directly uploadable via HTTP, but ZIPProcessor also
                        exposes `process_folder()` for the app layer to call when
                        a client sends a folder as a ZIP on-the-fly.

    The output is always a ZIP archive containing the cleaned PNGs in the same
    folder structure as the input.
    """

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """
        Process a ZIP file containing PNG slides.

        Args:
            upload_path: Path to the uploaded .zip file.
            output_path: Path where the cleaned .zip should be saved.
            filename:    Original filename (used for display only).

        Returns:
            dict with 'success', 'message', 'has_watermark', 'stats'.
        """
        logger.info(f"Processing ZIP file: {filename}")

        if not zipfile.is_zipfile(upload_path):
            return {"success": False, "error": "The uploaded file is not a valid ZIP archive."}

        with tempfile.TemporaryDirectory() as extract_dir:
            # Safe extraction: validate every member path to prevent Zip Slip
            with zipfile.ZipFile(upload_path, "r") as zf:
                extract_root = os.path.realpath(extract_dir)
                for member in zf.infolist():
                    # Resolve the target path and ensure it stays inside extract_dir
                    member_path = os.path.realpath(
                        os.path.join(extract_root, member.filename)
                    )
                    if not member_path.startswith(extract_root + os.sep) and member_path != extract_root:
                        logger.warning(f"Skipping unsafe ZIP entry: {member.filename!r}")
                        continue
                    zf.extract(member, extract_dir)

            result = self._process_png_tree(extract_dir, output_path, filename)

        return result

    def process_folder(self, folder_path: str, output_path: str, folder_name: str) -> dict:
        """
        Process an already-extracted folder of PNG slides and re-zip the output.

        Args:
            folder_path:  Absolute path to the source folder.
            output_path:  Where the output ZIP should be written.
            folder_name:  Display name (used in messages).
        """
        logger.info(f"Processing PNG folder: {folder_name}")
        return self._process_png_tree(folder_path, output_path, folder_name)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _process_png_tree(self, root_dir: str, output_zip_path: str, display_name: str) -> dict:
        """
        Walk root_dir, clean all PNG files, and write a ZIP to output_zip_path.
        Non-PNG files are copied verbatim to preserve folder structure.
        """
        png_total = 0
        png_cleaned = 0
        png_errors = 0

        with tempfile.TemporaryDirectory() as out_dir:
            # Walk source tree
            for dirpath, _, filenames in os.walk(root_dir):
                rel_dir = os.path.relpath(dirpath, root_dir)
                dest_dir = os.path.join(out_dir, rel_dir) if rel_dir != "." else out_dir
                os.makedirs(dest_dir, exist_ok=True)

                for fname in filenames:
                    src = os.path.join(dirpath, fname)
                    dst = os.path.join(dest_dir, fname)

                    if fname.lower().endswith(".png"):
                        png_total += 1
                        res = remove_png_watermark(src, dst)
                        if res["success"]:
                            png_cleaned += 1
                        else:
                            # Copy original if removal fails (don't lose the file)
                            shutil.copy2(src, dst)
                            png_errors += 1
                            logger.warning(f"PNG watermark removal failed for '{fname}': {res['error']}")
                    else:
                        # Copy non-PNG files as-is
                        shutil.copy2(src, dst)

            if png_total == 0:
                return {
                    "success": False,
                    "error": "No PNG files found in the uploaded archive or folder."
                }

            # Re-zip the cleaned output directory
            os.makedirs(os.path.dirname(output_zip_path), exist_ok=True) if os.path.dirname(output_zip_path) else None
            self._zip_directory(out_dir, output_zip_path)

        error_note = f" ({png_errors} failed, originals kept)" if png_errors else ""
        return {
            "success": True,
            "has_watermark": True,  # Always True — we always process and return a ZIP
            "message": (
                f"Processing finished! Cleaned {png_cleaned} of {png_total} PNG slides{error_note}."
            ),
            "stats": {
                "png_total": png_total,
                "png_cleaned": png_cleaned,
                "png_errors": png_errors,
            },
        }

    @staticmethod
    def _zip_directory(source_dir: str, output_zip_path: str):
        """Zip all contents of source_dir into output_zip_path."""
        with zipfile.ZipFile(output_zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for dirpath, _, filenames in os.walk(source_dir):
                for fname in filenames:
                    abs_path = os.path.join(dirpath, fname)
                    arc_path = os.path.relpath(abs_path, source_dir)
                    zf.write(abs_path, arc_path)


class PNGProcessor:
    """Handles PNG slide image watermark removal."""

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """
        Process a single PNG file for watermark removal.

        Returns dict with 'success', 'message', 'has_watermark', and 'stats'.
        """
        logger.info(f"Processing PNG file: {filename}")
        res = remove_png_watermark(upload_path, output_path)
        if not res["success"]:
            return {"success": False, "error": res.get("error", "PNG processing failed.")}

        return {
            "success": True,
            "has_watermark": True,
            "message": "Processing finished! Removed watermark from PNG slide.",
            "stats": {
                "png_cleaned": 1,
                "png_total": 1,
                "png_errors": 0,
            },
        }
