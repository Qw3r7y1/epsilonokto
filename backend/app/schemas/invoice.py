from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ── Line Items ───────────────────────────────────────────

class LineItemBase(BaseModel):
    description: str
    raw_quantity_text: Optional[str] = None
    cases: Optional[Decimal] = None
    units_per_case: Optional[Decimal] = None
    raw_quantity: Optional[Decimal] = None
    raw_unit: Optional[str] = None
    normalized_quantity: Optional[Decimal] = None
    normalized_unit: Optional[str] = None
    unit_price: Optional[Decimal] = None
    total_price: Optional[Decimal] = None
    normalized_unit_price: Optional[Decimal] = None
    position: Optional[int] = None


class LineItemOut(LineItemBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    product_id: Optional[UUID] = None


# ── Invoice ──────────────────────────────────────────────

class InvoiceBase(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    due_date: Optional[date] = None
    subtotal: Optional[Decimal] = None
    tax: Optional[Decimal] = None
    total: Optional[Decimal] = None
    currency: str = "USD"


class InvoiceOut(InvoiceBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    vendor_id: Optional[UUID] = None
    original_filename: str
    file_type: Optional[str] = None
    status: str
    extraction_confidence: Optional[Decimal] = None
    created_at: datetime
    line_items: list[LineItemOut] = []


class InvoiceListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    vendor_id: Optional[UUID] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    total: Optional[Decimal] = None
    currency: str
    status: str
    original_filename: str
    created_at: datetime


class UploadResponse(BaseModel):
    invoice_id: UUID
    filename: str
    status: str
    message: str
