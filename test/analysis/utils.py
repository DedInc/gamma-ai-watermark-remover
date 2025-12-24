"""Utility functions for PPTX analysis."""


def emu_to_inches(emu):
    """Convert EMUs to inches."""
    return emu / 914400


def get_shape_position_percentage(shape, slide_width, slide_height):
    """Calculate shape position as percentage of slide dimensions."""
    if shape.left is None or shape.top is None:
        return None, None, None, None

    left_pct = (shape.left / slide_width) * 100
    top_pct = (shape.top / slide_height) * 100
    right_pct = (
        ((shape.left + shape.width) / slide_width) * 100 if shape.width else left_pct
    )
    bottom_pct = (
        ((shape.top + shape.height) / slide_height) * 100 if shape.height else top_pct
    )

    return left_pct, top_pct, right_pct, bottom_pct


def is_bottom_right_corner(shape, slide_width, slide_height, threshold=70):
    """Check if shape is in bottom-right corner (>threshold% of dimensions)."""
    left_pct, top_pct, right_pct, bottom_pct = get_shape_position_percentage(
        shape, slide_width, slide_height
    )
    if left_pct is None:
        return False
    return left_pct >= threshold and top_pct >= threshold
