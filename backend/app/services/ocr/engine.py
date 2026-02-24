"""Tesseract OCR wrapper with basic image preprocessing."""

from pathlib import Path
from typing import Optional

import pytesseract
from PIL import Image, ImageFilter, ImageOps

from app.core.config import get_settings
from app.core.logging import get_logger

settings = get_settings()
log = get_logger(__name__)


def _preprocess(img: Image.Image) -> Image.Image:
    """Greyscale → sharpen → auto-contrast for better OCR accuracy."""
    img = ImageOps.grayscale(img)
    img = img.filter(ImageFilter.SHARPEN)
    img = ImageOps.autocontrast(img)
    return img


def ocr_image(image_path: Path, lang: Optional[str] = None) -> str:
    """Run Tesseract on a single image file and return extracted text."""
    lang = lang or settings.OCR_LANGUAGE
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD

    img = Image.open(image_path)
    img = _preprocess(img)

    config = f"--oem 3 --psm 6 -l {lang}"
    text = pytesseract.image_to_string(img, config=config)
    log.debug("OCR extracted %d chars from %s", len(text), image_path.name)
    return text


def ocr_image_bytes(data: bytes, lang: Optional[str] = None) -> str:
    """Run Tesseract on raw image bytes."""
    import io

    img = Image.open(io.BytesIO(data))
    img = _preprocess(img)

    lang = lang or settings.OCR_LANGUAGE
    pytesseract.pytesseract.tesseract_cmd = settings.TESSERACT_CMD
    config = f"--oem 3 --psm 6 -l {lang}"
    return pytesseract.image_to_string(img, config=config)
