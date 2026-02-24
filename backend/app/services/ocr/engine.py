import io

from PIL import Image
import pytesseract

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger("ocr.tesseract")
settings = get_settings()

pytesseract.pytesseract.tesseract_cmd = settings.tesseract_cmd


def extract_text_from_image(image_bytes: bytes) -> str:
    """Run Tesseract OCR on an image (PNG/JPEG/TIFF bytes)."""
    try:
        image = Image.open(io.BytesIO(image_bytes))

        # Convert to RGB if needed (e.g., RGBA PNGs)
        if image.mode not in ("L", "RGB"):
            image = image.convert("RGB")

        text = pytesseract.image_to_string(image, lang=settings.ocr_language)
        logger.info(f"OCR extracted {len(text)} chars")
        return text.strip()
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        return ""
