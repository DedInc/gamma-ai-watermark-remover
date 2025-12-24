"""
Test script for PPTX watermark detection and removal.

This script tests the PPTX watermark detector and remover using the sample Gamma PPTX file.
"""

import os
import sys

# Add the parent directory to the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processors.pptx.detector import PPTXWatermarkDetector
from processors.pptx.remover import PPTXWatermarkRemover


def main():
    # Paths
    sample_file = "Sample/Your-Tenant-Just-Sent-You-This-Photo.pptx"
    output_dir = "outputs"
    output_file = os.path.join(output_dir, "cleaned_presentation.pptx")

    # Check if sample file exists
    if not os.path.exists(sample_file):
        print(f"ERROR: Sample file not found: {sample_file}")
        return 1

    print("=" * 70)
    print("PPTX WATERMARK REMOVAL TEST")
    print("=" * 70)
    print(f"\nSample file: {sample_file}")
    print(f"Output file: {output_file}")

    # Initialize detector and remover
    detector = PPTXWatermarkDetector()
    remover = PPTXWatermarkRemover()

    # STEP 1: Detect watermarks in original file
    print("\n" + "=" * 70)
    print("STEP 1: DETECTING WATERMARKS IN ORIGINAL FILE")
    print("=" * 70)

    original_results = detector.detect_watermarks(sample_file)
    original_watermark_count = sum(1 for r in original_results if r["is_watermark"])

    print(f"\n>>> Original file has {original_watermark_count} watermark(s) detected")

    if original_watermark_count == 0:
        print("\nWARNING: No watermarks detected in the original file!")
        print("The file may not contain Gamma watermarks or detection failed.")

    # STEP 2: Remove watermarks
    print("\n" + "=" * 70)
    print("STEP 2: REMOVING WATERMARKS")
    print("=" * 70)

    result = remover.remove_watermarks(sample_file, output_file)

    if not result["success"]:
        print(f"\nERROR: Failed to remove watermarks: {result['error']}")
        return 1

    print("\n>>> Removal completed successfully!")
    print(f"    Watermarks removed: {result['watermarks_removed']}")
    print(f"    Layouts cleaned: {result['layouts_cleaned']}")
    print(f"    Masters cleaned: {result['masters_cleaned']}")

    # STEP 3: Verify removal by detecting watermarks in cleaned file
    print("\n" + "=" * 70)
    print("STEP 3: VERIFYING CLEANED FILE")
    print("=" * 70)

    cleaned_results = detector.detect_watermarks(output_file)
    cleaned_watermark_count = sum(1 for r in cleaned_results if r["is_watermark"])

    print(f"\n>>> Cleaned file has {cleaned_watermark_count} watermark(s) remaining")

    # STEP 4: Summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70)
    print(f"\nOriginal file watermarks: {original_watermark_count}")
    print(f"Cleaned file watermarks:  {cleaned_watermark_count}")
    print(
        f"Watermarks removed:       {original_watermark_count - cleaned_watermark_count}"
    )

    if cleaned_watermark_count == 0 and original_watermark_count > 0:
        print("\n[SUCCESS] All watermarks have been removed!")
        print(f"\nCleaned file saved to: {output_file}")
        return 0
    elif cleaned_watermark_count < original_watermark_count:
        print(
            f"\n[PARTIAL SUCCESS] Reduced watermarks from {original_watermark_count} to {cleaned_watermark_count}"
        )
        print(f"\nCleaned file saved to: {output_file}")
        return 0
    elif original_watermark_count == 0:
        print("\n[WARNING] No watermarks were detected in the original file.")
        print("    This may indicate the file doesn't have Gamma watermarks")
        print("    or the detection criteria need adjustment.")
        return 0
    else:
        print("\n[FAILURE] Watermarks could not be removed!")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
