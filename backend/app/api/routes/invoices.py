from uuid import UUID
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.db.models import Invoice
from app.schemas.invoice import InvoiceOut, InvoiceListOut, UploadResponse
from app.services.ingestion.pipeline import reprocess_invoice, process_invoice_async

router = APIRouter(prefix="/invoices", tags=["Invoices"])


@router.get("/", response_model=list[InvoiceListOut])
async def list_invoices(
    status: Optional[str] = Query(None, description="Filter by status"),
    vendor_id: Optional[UUID] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """List invoices with optional filters."""
    query = select(Invoice).order_by(Invoice.created_at.desc())

    if status:
        query = query.where(Invoice.status == status)
    if vendor_id:
        query = query.where(Invoice.vendor_id == vendor_id)

    query = query.limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{invoice_id}", response_model=InvoiceOut)
async def get_invoice(
    invoice_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a single invoice with its line items."""
    query = (
        select(Invoice)
        .options(selectinload(Invoice.line_items))
        .where(Invoice.id == invoice_id)
    )
    result = await db.execute(query)
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    return invoice


@router.post("/{invoice_id}/reprocess", response_model=UploadResponse)
async def trigger_reprocess(
    invoice_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Re-run extraction on an already-stored invoice file.

    Useful after correcting a vendor link, updating product catalog entries,
    or when an invoice previously failed or produced low-confidence output.

    The reprocess job runs in the background; the endpoint returns immediately
    with status='pending'.
    """
    result = await db.execute(select(Invoice).where(Invoice.id == invoice_id))
    invoice = result.scalar_one_or_none()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Reset to pending so callers can poll status
    invoice.status = "pending"
    await db.commit()

    background_tasks.add_task(process_invoice_async, invoice_id)

    return UploadResponse(
        invoice_id=invoice_id,
        filename=invoice.original_filename,
        status="pending",
        message="Reprocess job queued.",
    )
