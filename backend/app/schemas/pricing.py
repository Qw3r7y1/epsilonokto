from datetime import date
from typing import Optional

from pydantic import BaseModel

# Re-export comparison schemas for backwards compatibility
from app.schemas.vendor import PriceComparison, VendorPrice  # noqa: F401


class PriceHistoryEntry(BaseModel):
    """One data point in a product's price history."""

    date: Optional[date] = None
    vendor_name: str
    raw_quantity_text: Optional[str] = None
    raw_quantity: Optional[float] = None
    raw_unit: Optional[str] = None
    unit_price: Optional[float] = None
    normalized_unit_price: Optional[float] = None
    total_price: Optional[float] = None
    cases: Optional[float] = None
    units_per_case: Optional[float] = None
