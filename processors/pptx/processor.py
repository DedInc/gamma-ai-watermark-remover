"""High-level PPTX watermark processing."""

import logging

from processors.pptx.detector import PPTXWatermarkDetector
from processors.pptx.remover import PPTXWatermarkRemover

logger = logging.getLogger(__name__)


class PPTXProcessor:
    """Handles PPTX watermark detection and removal."""

    def __init__(self) -> None:
        self.detector = PPTXWatermarkDetector()
        self.remover = PPTXWatermarkRemover()

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """Process PPTX file for watermark detection and removal."""
        logger.info("Processing PPTX file: %s", filename)

        watermark_results = self.detector.detect_watermarks(upload_path)
        watermark_count = sum(1 for item in watermark_results if item["is_watermark"])
        logger.info("Detected %s watermarks in PPTX", watermark_count)

        if watermark_count == 0:
            return {
                "success": True,
                "has_watermark": False,
                "message": "Gamma.app watermarks not found in PowerPoint file.",
            }

        logger.info("Removing watermarks from PPTX...")
        result = self.remover.remove_watermarks(upload_path, output_path)
        if not result["success"]:
            return {"success": False, "error": result["error"]}

        slide_count_value = result.get("slide_count")
        slide_count = slide_count_value if isinstance(slide_count_value, int) else 0
        slide_info = f" across all {slide_count} slides" if slide_count > 0 else ""

        return {
            "success": True,
            "has_watermark": True,
            "message": (
                "Processing finished! Removed "
                f"{result['watermarks_removed']} watermarks "
                f"from {result['layouts_cleaned']} slide layouts{slide_info}."
            ),
            "stats": {
                "watermarks_removed": result["watermarks_removed"],
                "layouts_cleaned": result["layouts_cleaned"],
                "slides_cleaned": slide_count,
            },
        }
