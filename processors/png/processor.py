"""High-level PNG watermark processing."""

import logging

from processors.png.remover import remove_png_watermark

logger = logging.getLogger(__name__)


class PNGProcessor:
    """Handles PNG slide image watermark removal."""

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """Process a single PNG file for watermark removal."""
        logger.info("Processing PNG file: %s", filename)
        result = remove_png_watermark(upload_path, output_path)
        if not result["success"]:
            return {
                "success": False,
                "error": result.get("error", "PNG processing failed."),
            }

        return {
            "success": True,
            "has_watermark": True,
            "message": "Processing finished! Removed watermark from PNG slide.",
            "stats": {"png_cleaned": 1, "png_total": 1, "png_errors": 0},
        }
