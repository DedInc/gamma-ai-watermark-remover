"""
PNG Watermark Remover for Gamma.app watermarks.

Gamma PNG exports include a small 'Made with Gamma' badge/logo in the
bottom-right corner of every slide image.

Strategy:
  1. Detect the watermark region heuristically (bottom 10% height × right 20% width).
  2. For each row inside that region, sample a strip of pixels just to the LEFT
     of the region boundary to obtain the background colour for that row.
  3. Flood-fill each row of the watermark region with that sampled colour so the
     patch blends seamlessly with the slide background.

The algorithm is pure-PIL so there are no extra binary dependencies.
"""

import logging
import os

from PIL import Image

logger = logging.getLogger(__name__)


# Proportion of the slide that the watermark occupies (right/bottom edges)
WATERMARK_WIDTH_FRACTION = 0.22  # right 22 % of width
WATERMARK_HEIGHT_FRACTION = 0.10  # bottom 10 % of height

# How wide a sample strip to use when reading background colour (pixels)
SAMPLE_STRIP_WIDTH = 12


def _median_color(pixels: list[tuple]) -> tuple:
    """Return the per-channel median of a list of RGBA/RGB tuples."""
    if not pixels:
        return (255, 255, 255, 255)
    channels = len(pixels[0])
    medians = []
    for ch in range(channels):
        vals = sorted(p[ch] for p in pixels)
        mid = len(vals) // 2
        medians.append(vals[mid])
    return tuple(medians)


def remove_png_watermark(input_path: str, output_path: str) -> dict:
    """
    Remove Gamma watermark from a PNG slide image.

    Args:
        input_path:  Absolute path to the source PNG.
        output_path: Absolute path where the cleaned PNG is saved.

    Returns:
        dict with keys: success (bool), removed (bool), error (str|None)
    """
    result = {"success": False, "removed": False, "error": None}

    try:
        # Ensure absolute paths to avoid working-directory issues
        input_path = os.path.abspath(input_path)
        output_path = os.path.abspath(output_path)

        # Use context manager to ensure the file handle is released after loading
        with Image.open(input_path) as img_raw:
            img = img_raw.convert("RGBA")
        width, height = img.size

        # --- Define the watermark region ---
        wm_w = int(width * WATERMARK_WIDTH_FRACTION)
        wm_h = int(height * WATERMARK_HEIGHT_FRACTION)

        # Clamp to valid pixel range (at least 1px, at most full dimension)
        wm_w = max(1, min(wm_w, width))
        wm_h = max(1, min(wm_h, height))

        region_left = width - wm_w
        region_top = height - wm_h

        # Defensive: ensure region is within image bounds
        region_left = max(0, min(region_left, width - 1))
        region_top = max(0, min(region_top, height - 1))

        logger.info(
            f"PNG '{os.path.basename(input_path)}': size={width}x{height}, "
            f"watermark region x=[{region_left},{width}] y=[{region_top},{height}]"
        )

        pixels = img.load()

        # --- For each row in the watermark region, sample to the left and fill ---
        # Only sample when pixels exist left of the watermark boundary.
        # If region_left == 0, x=0 would be inside the watermark region itself.
        can_sample = region_left > 0
        sample_x_end = region_left - 1
        sample_x_start = max(0, region_left - SAMPLE_STRIP_WIDTH)

        rows_patched = 0
        for y in range(region_top, height):
            # Collect sample pixels to the left of the watermark boundary
            sample_pixels = []
            if can_sample and sample_x_start <= sample_x_end:
                for x in range(sample_x_start, sample_x_end + 1):
                    sample_pixels.append(pixels[x, y])

            fill_color = (
                _median_color(sample_pixels) if sample_pixels else (255, 255, 255, 255)
            )

            # Paint the entire watermark row with the sampled colour
            for x in range(region_left, width):
                pixels[x, y] = fill_color

            rows_patched += 1

        # Ensure output directory exists
        out_dir = os.path.dirname(output_path)
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)

        img.save(output_path, "PNG")

        logger.info(
            f"PNG watermark removed: {rows_patched} rows patched → {output_path}"
        )
        result["success"] = True
        result["removed"] = True
        return result

    except Exception as e:
        err = f"Error removing PNG watermark: {e}"
        logger.error(err)
        result["error"] = err
        return result
