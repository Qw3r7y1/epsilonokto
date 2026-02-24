import io

from PIL import Image, ImageFilter, ImageOps


def preprocess_for_ocr(image_bytes: bytes) -> bytes:
    """Basic preprocessing to improve OCR accuracy.

    Steps:
    - Convert to grayscale
    - Auto-contrast (normalize histogram)
    - Sharpen
    - Threshold to binary (optional, aggressive)

    Returns processed image as PNG bytes.
    """
    image = Image.open(io.BytesIO(image_bytes))

    # Grayscale
    image = ImageOps.grayscale(image)

    # Auto-contrast
    image = ImageOps.autocontrast(image)

    # Sharpen
    image = image.filter(ImageFilter.SHARPEN)

    # Save back to bytes
    buf = io.BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()
