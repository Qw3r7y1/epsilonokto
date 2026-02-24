import io

import fitz  # PyMuPDF
from PIL import Image

from app.core.logging import get_logger
from app.services.ocr.tesseract import extract_text_from_image

logger = get_logger("pdf.scanned_pdf")


def extract_text_from_scanned_pdf(pdf_bytes: bytes, dpi: int = 300) -> str:
    """Render each PDF page to an image and run OCR."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text = []

        for page_num, page in enumerate(doc):
            # Render page to pixmap at specified DPI
            zoom = dpi / 72  # 72 is default PDF DPI
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Convert pixmap to PNG bytes
            img_bytes = pix.tobytes("png")

            # OCR the rendered image
            text = extract_text_from_image(img_bytes)
            if text:
                pages_text.append(text)
                logger.info(f"Page {page_num + 1}: OCR extracted {len(text)} chars")

        doc.close()
        return "\n\n".join(pages_text).strip()
    except Exception as e:
        logger.error(f"Scanned PDF extraction failed: {e}")
        return ""
