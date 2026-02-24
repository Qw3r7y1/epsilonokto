import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.db.models import InvoiceStatus


class LineItemOut(BaseModel):
    id: uuid.UUID
    raw_description: Optional[str]
    raw_quantity: Optional[str]
    raw_unit: Optional[str]
    raw_unit_price: Optional[float]
    raw_total: Optional[float]
    cases: Optional[float]
    units_per_case: Optional[float]
    unit_size: Optional[float]
    unit_size_unit: Optional[str]
    total_base_quantity: Optional[float]
    price_per_base_unit: Optional[float]
    line_number: Optional[int]
    product_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: uuid.UUID
    vendor_id: Optional[uuid.UUID]
    filename: str
    invoice_number: Optional[str]
    invoice_date: Optional[datetime]
    total_amount: Optional[float]
    currency: str
    status: InvoiceStatus
    is_scanned: bool
    page_count: Optional[int]
    uploaded_at: datetime
    processed_at: Optional[datetime]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


class InvoiceDetailOut(InvoiceOut):
    ocr_text: Optional[str]
    line_items: list[LineItemOut] = []


class InvoiceListParams(BaseModel):
    vendor_id: Optional[uuid.UUID] = None
    status: Optional[InvoiceStatus] = None
    skip: int = 0
    limit: int = 50
