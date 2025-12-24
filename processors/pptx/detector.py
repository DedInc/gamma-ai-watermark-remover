"""
PPTX Watermark Detector for Gamma.app watermarks.

This module provides functionality to detect Gamma watermarks in PowerPoint (PPTX) files.
The watermarks are typically embedded in slide layouts as PNG images with hyperlinks to gamma.app.
"""

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class PPTXWatermarkDetector:
    """Detects Gamma watermarks in PPTX files."""

    def __init__(self, target_domain="gamma.app", corner_threshold=0.70):
        """
        Initialize the detector.

        Args:
            target_domain: The domain to look for in hyperlinks (default: "gamma.app")
            corner_threshold: The position threshold for bottom-right corner detection (default: 0.70)
        """
        self.target_domain = target_domain.lower()
        self.corner_threshold = corner_threshold

    def detect_watermarks(self, pptx_path):
        """
        Detect watermarks in a PPTX file.

        Args:
            pptx_path: Path to the PPTX file to analyze

        Returns:
            A list of dictionaries containing watermark detection results, each with:
                - location: "slide_layout" or "slide_master"
                - layout_name: Name of the layout
                - shape_name: Name of the shape
                - shape_type: Type of the shape
                - position: Dictionary with left, top, width, height in EMUs
                - position_percent: Dictionary with left_pct, top_pct values
                - hyperlink: The hyperlink URL if present
                - is_watermark: Boolean indicating if this is likely a watermark
        """
        results = []

        try:
            prs = Presentation(pptx_path)
            slide_width = prs.slide_width
            slide_height = prs.slide_height

            logger.info(f"Analyzing PPTX file: {pptx_path}")
            logger.info(f"Slide dimensions: {slide_width} x {slide_height} EMUs")
            logger.info(f"Target domain: {self.target_domain}")
            logger.info(f"Corner threshold: {self.corner_threshold * 100:.0f}%")

            # Iterate through all slide masters
            for master_idx, master in enumerate(prs.slide_masters):
                logger.info(f"\nSlide Master {master_idx + 1}:")

                # Check shapes in the slide master itself
                master_results = self._check_shapes(
                    shapes=master.shapes,
                    slide_width=slide_width,
                    slide_height=slide_height,
                    location_type="slide_master",
                    location_name=f"SlideMaster{master_idx + 1}",
                )
                results.extend(master_results)

                # Iterate through all slide layouts in this master
                for layout_idx, layout in enumerate(master.slide_layouts):
                    layout_name = (
                        layout.name if layout.name else f"Layout{layout_idx + 1}"
                    )
                    logger.info(f"  Checking Layout {layout_idx + 1}: {layout_name}")

                    layout_results = self._check_shapes(
                        shapes=layout.shapes,
                        slide_width=slide_width,
                        slide_height=slide_height,
                        location_type="slide_layout",
                        location_name=layout_name,
                    )
                    results.extend(layout_results)

            # Summary
            watermark_count = sum(1 for r in results if r["is_watermark"])
            logger.info(f"\n{'=' * 60}")
            logger.info("DETECTION SUMMARY:")
            logger.info(f"Total suspicious shapes found: {len(results)}")
            logger.info(f"Confirmed watermarks (gamma.app link): {watermark_count}")

            if watermark_count > 0:
                logger.info("\nWatermark locations:")
                for r in results:
                    if r["is_watermark"]:
                        logger.info(
                            f"  ✓ {r['location_name']}: {r['shape_name']} ({r['hyperlink']})"
                        )
            else:
                logger.info(f"\nNo {self.target_domain} watermarks detected.")

            return results

        except Exception as e:
            logger.error(f"Error detecting watermarks: {str(e)}")
            raise

    def _check_shapes(
        self, shapes, slide_width, slide_height, location_type, location_name
    ):
        """
        Check shapes for potential watermarks.

        Args:
            shapes: Collection of shapes to check
            slide_width: Width of the slide in EMUs
            slide_height: Height of the slide in EMUs
            location_type: Type of location ("slide_master" or "slide_layout")
            location_name: Name of the location

        Returns:
            List of detection results for shapes in corner positions
        """
        results = []

        for shape in shapes:
            # Only check picture shapes
            if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
                continue

            # Calculate position percentages
            left_pct = shape.left / slide_width if slide_width > 0 else 0
            top_pct = shape.top / slide_height if slide_height > 0 else 0

            # Check if in bottom-right corner
            is_in_corner = (
                left_pct >= self.corner_threshold and top_pct >= self.corner_threshold
            )

            if not is_in_corner:
                continue

            # Get hyperlink if present
            hyperlink_url = None
            has_gamma_link = False

            try:
                if hasattr(shape, "click_action") and shape.click_action:
                    if (
                        hasattr(shape.click_action, "hyperlink")
                        and shape.click_action.hyperlink
                    ):
                        hyperlink = shape.click_action.hyperlink
                        if hasattr(hyperlink, "address") and hyperlink.address:
                            hyperlink_url = hyperlink.address
                            has_gamma_link = self.target_domain in hyperlink_url.lower()
            except Exception as e:
                logger.debug(f"Could not get hyperlink for shape: {e}")

            # Determine if this is a watermark
            is_watermark = has_gamma_link

            result = {
                "location_type": location_type,
                "location_name": location_name,
                "shape_name": shape.name,
                "shape_type": str(shape.shape_type),
                "position": {
                    "left": shape.left,
                    "top": shape.top,
                    "width": shape.width,
                    "height": shape.height,
                },
                "position_percent": {
                    "left_pct": left_pct * 100,
                    "top_pct": top_pct * 100,
                },
                "hyperlink": hyperlink_url,
                "is_watermark": is_watermark,
            }

            if is_watermark:
                logger.info(
                    f"    ✓ Found watermark: {shape.name} at ({left_pct * 100:.1f}%, {top_pct * 100:.1f}%) -> {hyperlink_url}"
                )
            else:
                logger.debug(
                    f"    Corner image without gamma link: {shape.name} at ({left_pct * 100:.1f}%, {top_pct * 100:.1f}%)"
                )

            results.append(result)

        return results

    def has_watermarks(self, pptx_path):
        """
        Quick check if a PPTX file contains Gamma watermarks.

        Args:
            pptx_path: Path to the PPTX file

        Returns:
            True if watermarks are detected, False otherwise
        """
        try:
            results = self.detect_watermarks(pptx_path)
            return any(r["is_watermark"] for r in results)
        except Exception:
            return False

    def get_watermark_count(self, pptx_path):
        """
        Get the count of watermarks in a PPTX file.

        Args:
            pptx_path: Path to the PPTX file

        Returns:
            Number of watermarks detected
        """
        try:
            results = self.detect_watermarks(pptx_path)
            return sum(1 for r in results if r["is_watermark"])
        except Exception:
            return 0
