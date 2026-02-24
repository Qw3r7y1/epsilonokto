import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel


class LineItemOut(BaseModel):
    id: uuid.UUID
    description: str
    raw_quantity_text: Optional[str]
    cases: Optional[float]
    units_per_case: Optional[float]
    raw_quantity: Optional[float]
    raw_unit: Optional[str]
    normalized_quantity: Optional[float]
    normalized_unit: Optional[str]
    unit_price: Optional[float]
    total_price: Optional[float]
    normalized_unit_price: Optional[float]
    position: Optional[int]
    product_id: Optional[uuid.UUID]

    model_config = {"from_attributes": True}


class InvoiceOut(BaseModel):
    id: uuid.UUID
    vendor_id: Optional[uuid.UUID]
    original_filename: str
    file_type: Optional[str]
    invoice_number: Optional[str]
    invoice_date: Optional[date]
    due_date: Optional[date]
    subtotal: Optional[float]
    tax: Optional[float]
    total: Optional[float]
    currency: str
    status: str
    extraction_confidence: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceDetailOut(InvoiceOut):
    raw_text: Optional[str]
    line_items: list[LineItemOut] = []
