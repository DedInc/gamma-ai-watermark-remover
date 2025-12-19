"""
PPTX Watermark Remover for Gamma.app watermarks.

This module provides functionality to remove Gamma watermarks from PowerPoint (PPTX) files.
The watermarks are typically embedded in slide layouts as PNG images with hyperlinks to gamma.app.
"""

from pptx import Presentation
from pptx.enum.shapes import MSO_SHAPE_TYPE
import logging
import os

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class PPTXWatermarkRemover:
    """Removes Gamma watermarks from PPTX files."""
    
    def __init__(self, target_domain="gamma.app", corner_threshold=0.70):
        """
        Initialize the remover.
        
        Args:
            target_domain: The domain to look for in hyperlinks (default: "gamma.app")
            corner_threshold: The position threshold for bottom-right corner detection (default: 0.70)
        """
        self.target_domain = target_domain.lower()
        self.corner_threshold = corner_threshold
    
    def remove_watermarks(self, input_path, output_path):
        """
        Remove watermarks from a PPTX file and save to a new file.
        
        Args:
            input_path: Path to the input PPTX file
            output_path: Path to save the cleaned PPTX file
            
        Returns:
            A dictionary containing:
                - success: Boolean indicating if removal was successful
                - watermarks_removed: Number of watermarks removed
                - layouts_cleaned: Number of layouts that had watermarks removed
                - error: Error message if any
        """
        result = {
            'success': False,
            'watermarks_removed': 0,
            'layouts_cleaned': 0,
            'masters_cleaned': 0,
            'error': None
        }
        
        try:
            prs = Presentation(input_path)
            slide_width = prs.slide_width
            slide_height = prs.slide_height
            
            logger.info(f"Processing PPTX file: {input_path}")
            logger.info(f"Slide dimensions: {slide_width} x {slide_height} EMUs")
            logger.info(f"Target domain: {self.target_domain}")
            logger.info(f"Corner threshold: {self.corner_threshold * 100:.0f}%")
            
            total_removed = 0
            layouts_cleaned = 0
            masters_cleaned = 0
            
            # Iterate through all slide masters
            for master_idx, master in enumerate(prs.slide_masters):
                logger.info(f"\nSlide Master {master_idx + 1}:")
                
                # Remove watermarks from the slide master itself
                master_removed = self._remove_watermarks_from_shapes(
                    shapes=master.shapes,
                    slide_width=slide_width,
                    slide_height=slide_height,
                    location_name=f"SlideMaster{master_idx + 1}"
                )
                if master_removed > 0:
                    masters_cleaned += 1
                total_removed += master_removed
                
                # Iterate through all slide layouts in this master
                for layout_idx, layout in enumerate(master.slide_layouts):
                    layout_name = layout.name if layout.name else f"Layout{layout_idx + 1}"
                    logger.info(f"  Processing Layout {layout_idx + 1}: {layout_name}")
                    
                    layout_removed = self._remove_watermarks_from_shapes(
                        shapes=layout.shapes,
                        slide_width=slide_width,
                        slide_height=slide_height,
                        location_name=layout_name
                    )
                    
                    if layout_removed > 0:
                        layouts_cleaned += 1
                    total_removed += layout_removed
            
            # Ensure output directory exists
            output_dir = os.path.dirname(output_path)
            if output_dir and not os.path.exists(output_dir):
                os.makedirs(output_dir)
            
            # Save the cleaned presentation
            prs.save(output_path)
            
            result['success'] = True
            result['watermarks_removed'] = total_removed
            result['layouts_cleaned'] = layouts_cleaned
            result['masters_cleaned'] = masters_cleaned
            
            # Summary
            logger.info(f"\n{'='*60}")
            logger.info(f"REMOVAL SUMMARY:")
            logger.info(f"Watermarks removed: {total_removed}")
            logger.info(f"Layouts cleaned: {layouts_cleaned}")
            logger.info(f"Masters cleaned: {masters_cleaned}")
            logger.info(f"Output file: {output_path}")
            
            return result
            
        except Exception as e:
            error_msg = f"Error removing watermarks: {str(e)}"
            logger.error(error_msg)
            result['error'] = error_msg
            return result
    
    def _remove_watermarks_from_shapes(self, shapes, slide_width, slide_height, location_name):
        """
        Remove watermark shapes from a collection of shapes.
        
        Args:
            shapes: Collection of shapes to process
            slide_width: Width of the slide in EMUs
            slide_height: Height of the slide in EMUs
            location_name: Name of the location for logging
            
        Returns:
            Number of watermarks removed
        """
        shapes_to_remove = []
        
        for shape in shapes:
            # Only check picture shapes
            if shape.shape_type != MSO_SHAPE_TYPE.PICTURE:
                continue
            
            # Calculate position percentages
            left_pct = shape.left / slide_width if slide_width > 0 else 0
            top_pct = shape.top / slide_height if slide_height > 0 else 0
            
            # Check if in bottom-right corner
            is_in_corner = (left_pct >= self.corner_threshold and top_pct >= self.corner_threshold)
            
            if not is_in_corner:
                continue
            
            # Check for gamma hyperlink
            has_gamma_link = False
            hyperlink_url = None
            
            try:
                if hasattr(shape, 'click_action') and shape.click_action:
                    if hasattr(shape.click_action, 'hyperlink') and shape.click_action.hyperlink:
                        hyperlink = shape.click_action.hyperlink
                        if hasattr(hyperlink, 'address') and hyperlink.address:
                            hyperlink_url = hyperlink.address
                            has_gamma_link = self.target_domain in hyperlink_url.lower()
            except Exception as e:
                logger.debug(f"Could not get hyperlink for shape: {e}")
            
            # Remove if it has a gamma link OR if it's a small image in the corner
            # (some watermarks might not have accessible hyperlinks via python-pptx)
            should_remove = has_gamma_link
            
            # Also check for small images in corner that might be watermarks
            # Typical watermark size: ~1.7M x 0.4M EMUs
            if not should_remove and is_in_corner:
                # Check if it's a small image (likely a logo/watermark)
                if shape.width < 2000000 and shape.height < 600000:  # < ~2.2" x 0.66"
                    # Additional heuristic: check if it's in the extreme corner
                    if left_pct > 0.85 and top_pct > 0.90:
                        logger.info(f"    Found small corner image (potential watermark): {shape.name}")
                        should_remove = True
            
            if should_remove:
                shapes_to_remove.append((shape, hyperlink_url))
        
        # Remove the identified shapes
        removed_count = 0
        for shape, hyperlink_url in shapes_to_remove:
            try:
                # Get the XML element and remove it from its parent
                sp = shape._element
                parent = sp.getparent()
                if parent is not None:
                    parent.remove(sp)
                    removed_count += 1
                    if hyperlink_url:
                        logger.info(f"    ✓ Removed watermark: {shape.name} -> {hyperlink_url}")
                    else:
                        logger.info(f"    ✓ Removed corner image: {shape.name}")
            except Exception as e:
                logger.error(f"    ✗ Failed to remove shape {shape.name}: {e}")
        
        return removed_count
    
    def clean_pptx(self, input_path, output_path=None):
        """
        Convenience method to clean a PPTX file.
        
        Args:
            input_path: Path to the input PPTX file
            output_path: Path to save the cleaned file (optional, defaults to input_cleaned.pptx)
            
        Returns:
            Tuple of (output_path, error_message)
        """
        if output_path is None:
            base, ext = os.path.splitext(input_path)
            output_path = f"{base}_cleaned{ext}"
        
        result = self.remove_watermarks(input_path, output_path)
        
        if result['success']:
            return output_path, None
        else:
            return None, result['error']
