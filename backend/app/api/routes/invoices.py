import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.models import Invoice, InvoiceStatus
from app.db.session import get_db
from app.schemas.invoice import InvoiceDetailOut, InvoiceOut

router = APIRouter()


@router.get("/invoices", response_model=list[InvoiceOut])
def list_invoices(
    vendor_id: Optional[uuid.UUID] = Query(None),
    status: Optional[InvoiceStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    q = db.query(Invoice)
    if vendor_id:
        q = q.filter(Invoice.vendor_id == vendor_id)
    if status:
        q = q.filter(Invoice.status == status)
    return q.order_by(Invoice.uploaded_at.desc()).offset(skip).limit(limit).all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceDetailOut)
def get_invoice(invoice_id: uuid.UUID, db: Session = Depends(get_db)):
    invoice = db.get(Invoice, invoice_id)
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice
