"""
Invoice processing pipeline.

Flow:
  1. Load invoice record from DB
  2. Set status → "processing"
  3. Extract text (PDF native or OCR for scanned/image files) — CPU-bound
  4. Parse header fields (invoice number, date, due date, total, subtotal, tax)
  5. Detect vendor and link vendor_id when a confident match is found
  6. Extract line items, normalize quantities, match/create Products
  7. Persist everything and set status → "processed"
"""

import asyncio
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.models import Invoice, LineItem
from app.db.session import async_session
from app.services.extraction.invoice_parser import parse_invoice_fields
from app.services.extraction.line_items import extract_line_items
from app.services.ingestion.vendor_detect import detect_vendor
from app.services.ocr.engine import extract_text_from_image
from app.services.pdf.extractor import extract_pdf
from app.services.pricing.match import find_or_create_product

log = get_logger(__name__)

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff"}


def _extract_text(path: Path) -> tuple[str, int, bool]:
    """CPU-bound extraction — called via run_in_executor.

    Returns (text, page_count, is_scanned).
    """
    if path.suffix.lower() == ".pdf":
        result = extract_pdf(path)
        return result.text, result.page_count, result.is_scanned
    elif path.suffix.lower() in _IMAGE_SUFFIXES:
        text = extract_text_from_image(path.read_bytes())
        return text, 1, True
    else:
        raise ValueError(f"Unsupported file type: {path.suffix}")


async def process_invoice(invoice_id: uuid.UUID, db: AsyncSession) -> Invoice:
    """Process a single invoice: extract, parse, link, persist.

    Raises ValueError if the invoice record is not found.
    Any other exception sets status='failed' before re-raising.
    """
    invoice = await db.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    invoice.status = "processing"
    await db.flush()

    try:
        # ── 1. Text extraction (CPU-bound) ──────────────────────────────────
        path = Path(invoice.stored_path)
        loop = asyncio.get_event_loop()
        text, _page_count, _is_scanned = await loop.run_in_executor(
            None, _extract_text, path
        )
        invoice.raw_text = text

        # ── 2. Header field parsing ─────────────────────────────────────────
        fields = parse_invoice_fields(text)
        invoice.invoice_number = fields.get("invoice_number")
        invoice.invoice_date = fields.get("invoice_date")
        invoice.due_date = fields.get("due_date")
        invoice.total = fields.get("total")
        invoice.subtotal = fields.get("subtotal")
        invoice.tax = fields.get("tax")
        invoice.extraction_confidence = fields.get("confidence", 0)

        # ── 3. Vendor detection ─────────────────────────────────────────────
        if not invoice.vendor_id:
            vendor = await detect_vendor(text, db)
            if vendor:
                invoice.vendor_id = vendor.id

        # ── 4. Line item extraction + product matching ──────────────────────
        raw_items = extract_line_items(text)
        for raw in raw_items:
            description = raw.get("description") or "(no description)"

            item = LineItem(
                invoice_id=invoice_id,
                description=description,
                raw_quantity_text=raw.get("raw_quantity_text"),
                cases=raw.get("cases"),
                units_per_case=raw.get("units_per_case"),
                raw_quantity=raw.get("raw_quantity"),
                raw_unit=raw.get("raw_unit"),
                normalized_quantity=raw.get("normalized_quantity"),
                normalized_unit=raw.get("normalized_unit"),
                unit_price=raw.get("unit_price"),
                total_price=raw.get("total_price"),
                normalized_unit_price=raw.get("normalized_unit_price"),
                position=raw.get("position"),
            )

            product = await find_or_create_product(description, db)
            if product:
                item.product_id = product.id

            db.add(item)

        invoice.status = "processed"
        await db.flush()
        log.info(
            "Invoice %s processed: number=%s vendor_id=%s items=%d confidence=%.1f%%",
            invoice_id,
            invoice.invoice_number,
            invoice.vendor_id,
            len(raw_items),
            float(invoice.extraction_confidence or 0),
        )

    except Exception as exc:
        log.exception("Failed to process invoice %s: %s", invoice_id, exc)
        invoice.status = "failed"
        await db.flush()
        raise

    return invoice


async def process_invoice_async(invoice_id: uuid.UUID) -> None:
    """Background task entry point — owns its own session with commit/rollback."""
    async with async_session() as session:
        try:
            await process_invoice(invoice_id=invoice_id, db=session)
            await session.commit()
        except Exception:
            await session.rollback()
            log.exception(
                "Background processing failed for invoice %s", invoice_id
            )


async def reprocess_invoice(invoice_id: uuid.UUID, db: AsyncSession) -> Invoice:
    """Re-run extraction on an already-stored invoice file.

    Deletes existing line items before re-extracting so the slate is clean.
    Vendor detection runs again (existing vendor_id is cleared first so it
    is not skipped).
    """
    invoice = await db.get(Invoice, invoice_id)
    if not invoice:
        raise ValueError(f"Invoice {invoice_id} not found")

    # Remove stale line items
    existing_items = await db.execute(
        select(LineItem).where(LineItem.invoice_id == invoice_id)
    )
    for item in existing_items.scalars().all():
        await db.delete(item)

    # Clear vendor link so detection reruns fresh
    invoice.vendor_id = None
    await db.flush()

    return await process_invoice(invoice_id=invoice_id, db=db)
