"""Slide and master analysis for PPTX files."""

from .shape_analyzer import analyze_shape
from .utils import emu_to_inches


def analyze_slide_layout(layout, slide_width, slide_height):
    """Analyze a slide layout."""
    result = []
    result.append(f"\n  Layout: {layout.name}")

    for shape in layout.shapes:
        result.extend(analyze_shape(shape, slide_width, slide_height, indent=2))

    return result


def analyze_slide_master(master, slide_width, slide_height):
    """Analyze a slide master."""
    result = []
    result.append(
        f"\nSlide Master: {master.name if hasattr(master, 'name') else 'Unnamed'}"
    )

    # Analyze shapes on the master
    for shape in master.shapes:
        result.extend(analyze_shape(shape, slide_width, slide_height, indent=1))

    # Analyze layouts
    result.append("\n  Slide Layouts:")
    for layout in master.slide_layouts:
        result.extend(analyze_slide_layout(layout, slide_width, slide_height))

    return result


def analyze_slides(prs):
    """Analyze all slides in a presentation."""
    slide_width = prs.slide_width
    slide_height = prs.slide_height
    gamma_shapes = []

    print("\n" + "=" * 80)
    print("SLIDE ANALYSIS")
    print("=" * 80)

    for i, slide in enumerate(prs.slides):
        print(f"\n--- Slide {i + 1} ---")
        print(f"Slide layout: {slide.slide_layout.name}")
        print(f"Number of shapes: {len(slide.shapes)}")

        for shape in slide.shapes:
            from .shape_analyzer import analyze_hyperlinks
            from .utils import is_bottom_right_corner

            lines = analyze_shape(shape, slide_width, slide_height, indent=0)
            for line in lines:
                print(line)

            # Track gamma-related shapes
            if hasattr(shape, "text") and "gamma" in shape.text.lower():
                gamma_shapes.append((f"Slide {i + 1}", shape, "text"))

            hyperlinks = analyze_hyperlinks(shape)
            for link in hyperlinks:
                if "gamma" in link.lower():
                    gamma_shapes.append((f"Slide {i + 1}", shape, f"hyperlink: {link}"))

            # Check if in corner
            if is_bottom_right_corner(shape, slide_width, slide_height, 70):
                gamma_shapes.append((f"Slide {i + 1}", shape, "corner position"))

    return gamma_shapes


def print_slide_dimensions(prs):
    """Print slide dimensions."""
    slide_width = prs.slide_width
    slide_height = prs.slide_height

    print("\nSlide dimensions:")
    print(f"  Width: {slide_width} EMUs ({emu_to_inches(slide_width):.2f} inches)")
    print(f"  Height: {slide_height} EMUs ({emu_to_inches(slide_height):.2f} inches)")
    print(
        f"  Aspect ratio: {emu_to_inches(slide_width) / emu_to_inches(slide_height):.2f}:1"
    )
