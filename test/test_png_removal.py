"""
Pytest tests for PNG watermark removal.

Run with:  pytest test/test_png_removal.py -v
"""

from pathlib import Path
from typing import cast

from PIL import Image, ImageDraw
from PIL._typing import Coords

from utils.processors import PNGProcessor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_mock_png(path: str) -> None:
    """Create a 400x300 RGBA PNG with a simulated Gamma watermark badge."""
    img = Image.new("RGBA", (400, 300), (45, 90, 180, 255))
    draw = ImageDraw.Draw(img)
    # Watermark region: bottom-right 22% width x 10% height.
    draw.rectangle([320, 275, 390, 295], fill=(255, 255, 255, 255))
    img.save(path, "PNG")


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_png_watermark_removal_success(tmp_path: Path) -> None:
    """PNGProcessor.process() should return success=True and write an output file."""
    input_png = tmp_path / "input.png"
    output_png = tmp_path / "output.png"

    _create_mock_png(str(input_png))

    processor = PNGProcessor()
    result = processor.process(str(input_png), str(output_png), "input.png")

    assert result["success"] is True, f"Processing failed: {result.get('error')}"
    assert output_png.exists(), "Output file was not created"


def test_png_watermark_region_painted_over(tmp_path: Path) -> None:
    """The watermark region should be painted with the background colour."""
    input_png = tmp_path / "input.png"
    output_png = tmp_path / "output.png"

    _create_mock_png(str(input_png))

    processor = PNGProcessor()
    processor.process(str(input_png), str(output_png), "input.png")

    cleaned = Image.open(str(output_png)).convert("RGBA")
    # Pixel (350, 285) was white in the input (watermark badge)
    r, g, b, _ = cast(Coords, cleaned.getpixel((350, 285)))
    # Should now match the slide background colour (45, 90, 180)
    assert (r, g, b) == (45, 90, 180), (
        f"Expected background colour (45, 90, 180) but got ({r}, {g}, {b})"
    )


def test_png_processor_has_watermark_flag(tmp_path: Path) -> None:
    """has_watermark should be True for a PNG that was processed."""
    input_png = tmp_path / "input.png"
    output_png = tmp_path / "output.png"

    _create_mock_png(str(input_png))

    result = PNGProcessor().process(str(input_png), str(output_png), "input.png")
    assert result.get("has_watermark") is True
