"""PPTX watermark detection and removal."""

from processors.pptx.detector import PPTXWatermarkDetector
from processors.pptx.remover import PPTXWatermarkRemover

__all__ = ["PPTXWatermarkDetector", "PPTXWatermarkRemover"]
