import uuid
from typing import Optional

from pydantic import BaseModel


class VendorPricePoint(BaseModel):
    vendor_id: uuid.UUID
    vendor_name: str
    invoice_id: uuid.UUID
    invoice_date: Optional[str]
    raw_quantity: Optional[str]
    raw_unit_price: Optional[float]
    total_base_quantity: Optional[float]
    price_per_base_unit: Optional[float]
    base_unit: Optional[str]


class PriceComparisonOut(BaseModel):
    product_id: uuid.UUID
    product_name: str
    compare_mode: str
    base_unit: Optional[str]
    vendors: list[VendorPricePoint]
