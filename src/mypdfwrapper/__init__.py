# src/mypdfwrapper/__init__.py
import fitz as pymupdf
from .pdf_extractor import extract_text

__all__ = ["extract_text", "pymupdf"]
