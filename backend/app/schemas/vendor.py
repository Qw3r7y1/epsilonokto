from datetime import datetime
from uuid import UUID
from typing import Optional

from pydantic import BaseModel, ConfigDict


class VendorBase(BaseModel):
    name: str
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorOut(VendorBase):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    normalized_name: str
    created_at: datetime


class PriceComparison(BaseModel):
    """One product across multiple vendors with normalized pricing."""
    product_name: str
    compare_mode: str  # weight, volume, count, none
    display_unit: str  # lb, kg, L, ea, etc.
    vendors: list["VendorPrice"]


class VendorPrice(BaseModel):
    vendor_name: str
    vendor_id: str
    avg_price_per_display_unit: Optional[float] = None
    min_price_per_display_unit: Optional[float] = None
    max_price_per_display_unit: Optional[float] = None
    invoice_count: int
    last_seen: Optional[datetime] = None
    raw_unit: Optional[str] = None
    raw_avg_unit_price: Optional[float] = None
