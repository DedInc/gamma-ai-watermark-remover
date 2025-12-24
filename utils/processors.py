"""Document processing logic for PDF and PPTX files."""

import logging

from processors.pdf.detector import WatermarkDetector
from processors.pdf.remover import WatermarkRemover
from processors.pptx.detector import PPTXWatermarkDetector
from processors.pptx.remover import PPTXWatermarkRemover

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

            return {
                "success": True,
                "has_watermark": True,
                "message": (
                    f"Processing finished! Removed {result['watermarks_removed']} watermarks "
                    f"from {result['layouts_cleaned']} layouts."
                ),
                "stats": {
                    "watermarks_removed": result["watermarks_removed"],
                    "layouts_cleaned": result["layouts_cleaned"],
                },
            }
        else:
            return {
                "success": True,
                "has_watermark": False,
                "message": "Gamma.app watermarks not found in PowerPoint file.",
            }
