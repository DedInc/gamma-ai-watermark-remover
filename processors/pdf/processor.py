"""High-level PDF watermark processing."""

import logging

from processors.pdf.detector import WatermarkDetector
from processors.pdf.remover import WatermarkRemover

logger = logging.getLogger(__name__)


class PDFProcessor:
    """Handles PDF watermark detection and removal."""

    def __init__(self) -> None:
        self.detector = WatermarkDetector()
        self.remover = WatermarkRemover()

    def process(self, upload_path: str, output_path: str, filename: str) -> dict:
        """Process PDF file for watermark detection and removal."""
        logger.info("Processing PDF file: %s", filename)
        elements_to_remove, error = self.detector.identify_watermarks(upload_path)

        if error:
            return {"success": False, "error": error}

        if not elements_to_remove:
            return {
                "success": True,
                "has_watermark": False,
                "message": "Gamma.app watermarks not found in PDF.",
            }

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
