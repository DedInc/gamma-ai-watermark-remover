"""Compatibility exports for high-level document processors."""

from processors.keynote.processor import KeynoteProcessor
from processors.pdf.processor import PDFProcessor
from processors.png.processor import PNGProcessor
from processors.pptx.processor import PPTXProcessor
from processors.zip_processor import ZIPProcessor

__all__ = [
    "KeynoteProcessor",
    "PDFProcessor",
    "PNGProcessor",
    "PPTXProcessor",
    "ZIPProcessor",
]
