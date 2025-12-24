#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""PPTX Watermark Analysis Script"""

import sys
import io

from pptx import Presentation

from analysis.slide_analyzer import (
    analyze_slides,
    analyze_slide_master,
    print_slide_dimensions,
)
from analysis.xml_analyzer import extract_and_analyze_xml
from analysis.utils import get_shape_position_percentage

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Constants
PPTX_FILE = r"Sample\Your-Tenant-Just-Sent-You-This-Photo.pptx"


def print_watermark_summary(gamma_shapes, prs):
    """Print summary of detected watermarks."""
    print("\n" + "=" * 80)
    print("WATERMARK DETECTION SUMMARY")
    print("=" * 80)

    if gamma_shapes:
        print("\nPotential watermark shapes found:")
        for location, shape, reason in gamma_shapes:
            print(f"  - {location}: '{shape.name}' ({reason})")
            if shape.left is not None:
                left_pct, top_pct, right_pct, bottom_pct = (
                    get_shape_position_percentage(
                        shape, prs.slide_width, prs.slide_height
                    )
                )
                print(
                    f"    Position: {left_pct:.1f}%-{right_pct:.1f}% horizontal, "
                    f"{top_pct:.1f}%-{bottom_pct:.1f}% vertical"
                )
    else:
        print("\nNo obvious gamma watermark shapes found in slides.")
        print("Watermark may be in slide masters, layouts, or embedded differently.")


def main():
    print("=" * 80)
    print("GAMMA PPTX WATERMARK ANALYSIS")
    print("=" * 80)
    print(f"\nAnalyzing file: {PPTX_FILE}")

    # Open the presentation
    prs = Presentation(PPTX_FILE)

    # Print slide dimensions
    print_slide_dimensions(prs)

    # Analyze slides
    gamma_shapes = analyze_slides(prs)

    # Analyze slide masters
    print("\n" + "=" * 80)
    print("SLIDE MASTER ANALYSIS")
    print("=" * 80)

    for master in prs.slide_masters:
        lines = analyze_slide_master(master, prs.slide_width, prs.slide_height)
        for line in lines:
            print(line)

    # Extract and analyze XML
    xml_results = extract_and_analyze_xml(PPTX_FILE)
    for line in xml_results:
        print(line)

    # Print summary
    print_watermark_summary(gamma_shapes, prs)


if __name__ == "__main__":
    main()
