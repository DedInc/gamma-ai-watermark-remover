"""Watermark detection and removal processors."""

from processors.pdf.detector import WatermarkDetector
from processors.pdf.remover import WatermarkRemover
from processors.pptx.detector import PPTXWatermarkDetector
from processors.pptx.remover import PPTXWatermarkRemover

__all__ = [
    "WatermarkDetector",
    "WatermarkRemover",
    "PPTXWatermarkDetector",
    "PPTXWatermarkRemover",
]
