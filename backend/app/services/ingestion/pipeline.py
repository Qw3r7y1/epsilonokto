"""
Invoice processing pipeline.

Flow:
  1. Load invoice record from DB
  2. Detect file type (PDF vs image)
  3. Extract text — CPU-bound, runs in a thread executor
  4. Parse invoice fields and line items
  5. Persist extracted data back to DB
"""

import asyncio
import uuid
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Invoice, LineItem
from app.db.session import async_session
from app.services.extraction.parser import parse_invoice_text
from app.services.ocr.engine import extract_text_from_image
from app.services.pdf.extractor import extract_pdf

log = get_logger(__name__)

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _extract_text(path: Path) -> tuple[str, int, bool]:
    """CPU-bound extraction — called via run_in_executor."""
    if path.suffix.lower() == ".pdf":
        result = extract_pdf(path)
        return result.text, result.page_count, result.is_scanned
    elif path.suffix.lower() in _IMAGE_SUFFIXES:
        text = extract_text_from_image(path.read_bytes())
        return text, 1, True
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")


async def process_invoice(invoice_id: uuid.UUID, db: AsyncSession) -> Invoice:
    invoice = await db.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    invoice.status = "processing"
    await db.flush()

    try:
        path = Path(invoice.stored_path)
        loop = asyncio.get_event_loop()
        text, _page_count, _is_scanned = await loop.run_in_executor(
            None, _extract_text, path
        )

        invoice.raw_text = text

        parsed = parse_invoice_text(text)
        invoice.invoice_number = parsed.invoice_number
        if parsed.invoice_date:
            invoice.invoice_date = parsed.invoice_date.date()
        invoice.total = parsed.total_amount

        for raw in parsed.line_items:
            pq = raw.parsed_quantity
            item = LineItem(
                invoice_id=invoice_id,
                description=raw.description or "(no description)",
                raw_quantity_text=raw.raw_quantity,
                unit_price=raw.raw_unit_price,
                total_price=raw.raw_total,
                position=raw.line_number,
            )
            if pq:
                item.cases = pq.cases
                item.units_per_case = pq.units_per_case
                item.raw_quantity = pq.total_quantity
                item.raw_unit = pq.raw_unit
                item.normalized_quantity = pq.normalized_quantity
                item.normalized_unit = pq.normalized_unit
                if pq.normalized_quantity and raw.raw_total:
                    item.normalized_unit_price = raw.raw_total / pq.normalized_quantity
            db.add(item)

        invoice.status = "processed"
        await db.flush()
        log.info("Invoice %s processed successfully", invoice_id)

    except Exception as exc:
        log.exception("Failed to process invoice %s: %s", invoice_id, exc)
        invoice.status = "failed"
        await db.flush()
        raise

    return invoice


async def process_invoice_async(invoice_id: uuid.UUID) -> None:
    """Background task — opens its own session with commit/rollback."""
    async with async_session() as session:
        try:
            await process_invoice(invoice_id=invoice_id, db=session)
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception("Background processing failed for invoice %s", invoice_id)
