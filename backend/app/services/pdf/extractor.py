"""
PDF text extraction.

- Text PDFs  → PyMuPDF (fast, accurate)
- Scanned PDFs → convert each page to image → Tesseract OCR
"""

from pathlib import Path
from typing import NamedTuple

import fitz  # PyMuPDF

from app.core.logging import get_logger
from app.services.ocr.engine import extract_text_from_image

log = get_logger(__name__)

_TEXT_THRESHOLD = 50  # Minimum chars per page to consider it a text PDF
_OCR_DPI = 300


class ExtractionResult(NamedTuple):
    text: str
    page_count: int
    is_scanned: bool


def extract_pdf(path: Path) -> ExtractionResult:
    """Extract full text from a PDF, auto-detecting text vs. scanned."""
    doc = fitz.open(str(path))
    page_count = len(doc)

    pages_text: list[str] = []
    scanned_pages = 0

    for page in doc:
        text = page.get_text("text")
        if len(text.strip()) >= _TEXT_THRESHOLD:
            pages_text.append(text)
        else:
            # Render page as image and OCR
            scanned_pages += 1
            pix = page.get_pixmap(dpi=_OCR_DPI)
            img_bytes = pix.tobytes("png")
            ocr_text = extract_text_from_image(img_bytes)
            pages_text.append(ocr_text)
            log.debug("Page %d is scanned, used OCR", page.number + 1)

    doc.close()

    full_text = "\n\n".join(pages_text)
    is_scanned = scanned_pages > (page_count / 2)
    log.info(
        "Extracted %d chars from %s (%d pages, %d scanned)",
        len(full_text),
        path.name,
        page_count,
        scanned_pages,
    )
    return ExtractionResult(text=full_text, page_count=page_count, is_scanned=is_scanned)
