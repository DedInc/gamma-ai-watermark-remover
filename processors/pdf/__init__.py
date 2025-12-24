"""PDF watermark detection and removal."""

from processors.pdf.detector import WatermarkDetector
from processors.pdf.remover import WatermarkRemover

__all__ = ["WatermarkDetector", "WatermarkRemover"]
