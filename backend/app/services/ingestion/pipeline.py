"""
Invoice processing pipeline.

Flow:
  1. Load invoice record from DB
  2. Detect file type (PDF vs image)
  3. Extract text (PyMuPDF for text PDFs, Tesseract for scanned/images)
  4. Parse invoice fields and line items
  5. Persist extracted data back to DB
"""

import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.db.models import Invoice, InvoiceLineItem, InvoiceStatus
from app.db.session import SessionLocal
from app.services.extraction.parser import parse_invoice_text
from app.services.ocr.engine import ocr_image
from app.services.pdf.extractor import extract_pdf

log = get_logger(__name__)

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _extract_text(path: Path) -> tuple[str, int, bool]:
    """Return (text, page_count, is_scanned)."""
    if path.suffix.lower() == ".pdf":
        result = extract_pdf(path)
        return result.text, result.page_count, result.is_scanned
    elif path.suffix.lower() in _IMAGE_SUFFIXES:
        text = ocr_image(path)
        return text, 1, True
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")


def process_invoice(invoice_id: uuid.UUID, db: Session) -> Invoice:
    """Synchronous pipeline — runs inside the provided DB session."""
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    invoice.status = InvoiceStatus.processing
    db.commit()

    try:
        path = Path(invoice.file_path)
        text, page_count, is_scanned = _extract_text(path)

        invoice.ocr_text = text
        invoice.page_count = page_count
        invoice.is_scanned = is_scanned

        parsed = parse_invoice_text(text)
        invoice.invoice_number = parsed.invoice_number
        invoice.invoice_date = parsed.invoice_date
        invoice.total_amount = parsed.total_amount

        # Persist line items
        for raw in parsed.line_items:
            pq = raw.parsed_quantity
            item = InvoiceLineItem(
                invoice_id=invoice_id,
                raw_description=raw.description,
                raw_quantity=raw.raw_quantity,
                raw_unit_price=raw.raw_unit_price,
                raw_total=raw.raw_total,
                line_number=raw.line_number,
            )
            if pq:
                item.cases = pq.cases
                item.units_per_case = pq.units_per_case
                item.unit_size = pq.unit_size
                item.unit_size_unit = pq.unit_size_unit
                item.total_base_quantity = pq.total_base_quantity
                if pq.total_base_quantity and raw.raw_unit_price:
                    item.price_per_base_unit = (
                        raw.raw_total / pq.total_base_quantity
                        if pq.total_base_quantity
                        else None
                    )
            db.add(item)

        invoice.status = InvoiceStatus.extracted
        invoice.processed_at = datetime.now(timezone.utc)
        db.commit()
        log.info("Invoice %s processed successfully", invoice_id)

    except Exception as exc:
        log.exception("Failed to process invoice %s: %s", invoice_id, exc)
        invoice.status = InvoiceStatus.failed
        invoice.error_message = str(exc)
        db.commit()
        raise

    return invoice


async def process_invoice_async(invoice_id: uuid.UUID) -> None:
    """Async wrapper — opens its own DB session for background task use."""
    db = SessionLocal()
    try:
        process_invoice(invoice_id=invoice_id, db=db)
    finally:
        db.close()
