"""Vendor price comparison service.

Compares prices across vendors using normalized units:
  - Weight products: compare per-gram (display in preferred unit)
  - Volume products: compare per-ml (display in preferred unit)
  - Count products:  compare per-unit
  - "none" mode:     show raw prices side by side, no conversion
"""

from decimal import Decimal

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import LineItem, Invoice, Vendor, Product
from app.core.logging import get_logger

logger = get_logger("pricing.compare")


async def compare_product_prices(
    db: AsyncSession,
    product_name: str | None = None,
    category: str | None = None,
    vendor_id: str | None = None,
) -> list[dict]:
    """Compare prices for products across vendors.

    For products with compare_mode = "weight" or "volume":
      uses normalized_unit_price (per gram or per ml)
      converts to display unit (kg, oz, L, etc.)

    For compare_mode = "count":
      uses normalized_unit_price (per unit)

    For compare_mode = "none":
      shows raw unit_price and raw_unit as-is
    """
    query = (
        select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.compare_mode,
            Product.base_unit,
            Vendor.name.label("vendor_name"),
            Vendor.id.label("vendor_id"),
            func.avg(LineItem.normalized_unit_price).label("avg_normalized_price"),
            func.avg(LineItem.unit_price).label("avg_raw_price"),
            func.min(LineItem.normalized_unit_price).label("min_normalized_price"),
            func.max(LineItem.normalized_unit_price).label("max_normalized_price"),
            func.count(LineItem.id).label("invoice_count"),
            func.max(Invoice.invoice_date).label("last_seen"),
            func.mode().within_group(LineItem.raw_unit).label("common_raw_unit"),
        )
        .join(LineItem, LineItem.product_id == Product.id)
        .join(Invoice, LineItem.invoice_id == Invoice.id)
        .join(Vendor, Invoice.vendor_id == Vendor.id)
        .group_by(
            Product.id, Product.name, Product.compare_mode, Product.base_unit,
            Vendor.name, Vendor.id,
        )
        .order_by(Product.name, func.avg(LineItem.normalized_unit_price))
    )

    if product_name:
        query = query.where(Product.normalized_name.ilike(f"%{product_name}%"))
    if category:
        query = query.where(Product.category == category)
    if vendor_id:
        query = query.where(Vendor.id == vendor_id)

    result = await db.execute(query)
    rows = result.all()

    # Group by product
    products: dict[str, dict] = {}
    for row in rows:
        key = str(row.product_id)
        compare_mode = row.compare_mode or "none"

        if key not in products:
            display_unit = row.base_unit or _default_display_unit(compare_mode)
            products[key] = {
                "product_name": row.product_name,
                "compare_mode": compare_mode,
                "display_unit": display_unit,
                "vendors": [],
            }

        display_unit = products[key]["display_unit"]

        products[key]["vendors"].append({
            "vendor_name": row.vendor_name,
            "vendor_id": str(row.vendor_id),
            "avg_price_per_display_unit": _to_display_price(
                row.avg_normalized_price, compare_mode, display_unit
            ),
            "min_price_per_display_unit": _to_display_price(
                row.min_normalized_price, compare_mode, display_unit
            ),
            "max_price_per_display_unit": _to_display_price(
                row.max_normalized_price, compare_mode, display_unit
            ),
            "invoice_count": row.invoice_count,
            "last_seen": row.last_seen,
            "raw_unit": row.common_raw_unit,
            "raw_avg_unit_price": float(row.avg_raw_price) if row.avg_raw_price else None,
        })

    return list(products.values())


async def get_price_history(
    db: AsyncSession,
    product_id: str,
    vendor_id: str | None = None,
) -> list[dict]:
    """Get price history for a specific product over time."""
    query = (
        select(
            Invoice.invoice_date,
            Vendor.name.label("vendor_name"),
            LineItem.raw_quantity,
            LineItem.raw_unit,
            LineItem.unit_price,
            LineItem.normalized_unit_price,
            LineItem.total_price,
            LineItem.cases,
            LineItem.units_per_case,
            LineItem.raw_quantity_text,
        )
        .join(Invoice, LineItem.invoice_id == Invoice.id)
        .join(Vendor, Invoice.vendor_id == Vendor.id)
        .where(LineItem.product_id == product_id)
        .order_by(Invoice.invoice_date)
    )

    if vendor_id:
        query = query.where(Vendor.id == vendor_id)

    result = await db.execute(query)
    rows = result.all()

    return [
        {
            "date": row.invoice_date,
            "vendor_name": row.vendor_name,
            "raw_quantity_text": row.raw_quantity_text,
            "raw_quantity": float(row.raw_quantity) if row.raw_quantity else None,
            "raw_unit": row.raw_unit,
            "unit_price": float(row.unit_price) if row.unit_price else None,
            "normalized_unit_price": float(row.normalized_unit_price) if row.normalized_unit_price else None,
            "total_price": float(row.total_price) if row.total_price else None,
            "cases": float(row.cases) if row.cases else None,
            "units_per_case": float(row.units_per_case) if row.units_per_case else None,
        }
        for row in rows
    ]


def _default_display_unit(compare_mode: str) -> str:
    return {"weight": "lb", "volume": "L", "count": "ea", "none": ""}.get(compare_mode, "")


def _to_display_price(
    normalized_price: float | None,
    compare_mode: str,
    display_unit: str,
) -> float | None:
    """Convert price-per-base-unit to price-per-display-unit.

    normalized_price is per gram (weight) or per ml (volume) or per unit (count).
    Multiply by the display unit size to get price per display unit.
    e.g., price_per_gram * 453.592 = price_per_lb
    """
    if normalized_price is None:
        return None

    from app.services.units import WEIGHT_TO_GRAMS, VOLUME_TO_ML

    price = Decimal(str(normalized_price))
    unit_lower = display_unit.lower()

    if compare_mode == "weight" and unit_lower in WEIGHT_TO_GRAMS:
        factor = WEIGHT_TO_GRAMS[unit_lower]
        return float((price * factor).quantize(Decimal("0.01")))

    if compare_mode == "volume" and unit_lower in VOLUME_TO_ML:
        factor = VOLUME_TO_ML[unit_lower]
        return float((price * factor).quantize(Decimal("0.01")))

    return float(price.quantize(Decimal("0.01"))) if price else None
