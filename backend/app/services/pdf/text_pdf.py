import fitz  # PyMuPDF

from app.core.logging import get_logger

logger = get_logger("pdf.text_pdf")


def extract_text_from_pdf(pdf_bytes: bytes) -> str:
    """Extract text from a text-layer PDF using PyMuPDF."""
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages = []
        for page_num, page in enumerate(doc):
            text = page.get_text("text")
            if text.strip():
                pages.append(text)
        doc.close()

        full_text = "\n\n".join(pages)
        logger.info(f"PyMuPDF extracted {len(full_text)} chars from {len(pages)} pages")
        return full_text.strip()
    except Exception as e:
        logger.error(f"PyMuPDF extraction failed: {e}")
        return ""
