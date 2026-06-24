"""High-level Keynote watermark processing."""

import logging
import os
import tempfile

from processors.keynote.converter import key_to_pptx, pptx_to_key
from processors.pptx.processor import PPTXProcessor

logger = logging.getLogger(__name__)


class KeynoteProcessor:
    """Handles .key watermark removal on macOS via Keynote.app."""

    def __init__(self) -> None:
        self.pptx_processor = PPTXProcessor()

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """Convert .key to PPTX, clean it, then convert back to .key."""
        logger.info("Processing Keynote file: %s", filename)
        base = os.path.splitext(filename)[0]

        with tempfile.TemporaryDirectory() as tmpdir:
            tmp_pptx = os.path.join(tmpdir, f"{base}.pptx")
            conv_result = key_to_pptx(upload_path, tmp_pptx)
            if not conv_result["success"]:
                return {"success": False, "error": conv_result["error"]}

            tmp_cleaned_pptx = os.path.join(tmpdir, f"{base}_cleaned.pptx")
            proc_result = self.pptx_processor.process(
                tmp_pptx, tmp_cleaned_pptx, f"{base}.pptx"
            )

            if not proc_result["success"]:
                return {
                    "success": False,
                    "error": proc_result.get("error", "PPTX processing failed."),
                }
            if not proc_result["has_watermark"]:
                return {
                    "success": True,
                    "has_watermark": False,
                    "message": (
                        "Gamma.app watermarks not found in Keynote presentation."
                    ),
                }

            save_result = pptx_to_key(tmp_cleaned_pptx, output_path)
            if not save_result["success"]:
                return {"success": False, "error": save_result["error"]}

        stats = proc_result.get("stats", {})
        return {
            "success": True,
            "has_watermark": True,
            "message": (
                "Processing finished! Removed "
                f"{stats.get('watermarks_removed', '?')} watermarks "
                "and saved clean Keynote file."
            ),
            "stats": stats,
        }
