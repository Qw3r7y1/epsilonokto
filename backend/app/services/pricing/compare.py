"""Vendor price comparison — aggregated per product × vendor."""

import uuid
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice, LineItem, Product, Vendor
from app.schemas.vendor import PriceComparison, VendorPrice

_DEFAULT_UNIT: dict[str, str] = {
    "weight": "g",
    "volume": "ml",
    "count": "ea",
    "none": "ea",
}


async def compare_prices(
    db: AsyncSession,
    product_id: Optional[uuid.UUID] = None,
) -> list[PriceComparison]:
    q = (
        select(
            Product.id.label("product_id"),
            Product.name.label("product_name"),
            Product.compare_mode,
            Product.base_unit,
            Vendor.id.label("vendor_id"),
            Vendor.name.label("vendor_name"),
            func.avg(LineItem.normalized_unit_price).label("avg_price"),
            func.min(LineItem.normalized_unit_price).label("min_price"),
            func.max(LineItem.normalized_unit_price).label("max_price"),
            func.count(Invoice.id.distinct()).label("invoice_count"),
            func.max(Invoice.invoice_date).label("last_seen"),
            func.avg(LineItem.unit_price).label("raw_avg_unit_price"),
        )
        .select_from(LineItem)
        .join(Invoice, LineItem.invoice_id == Invoice.id)
        .join(Vendor, Invoice.vendor_id == Vendor.id)
        .join(Product, LineItem.product_id == Product.id)
        .where(LineItem.product_id.isnot(None))
        .where(Invoice.vendor_id.isnot(None))
        .group_by(
            Product.id,
            Product.name,
            Product.compare_mode,
            Product.base_unit,
            Vendor.id,
            Vendor.name,
        )
        .order_by(Product.id, Vendor.name)
    )

    if product_id:
        q = q.where(LineItem.product_id == product_id)

    result = await db.execute(q)
    rows = result.all()

    products: dict[uuid.UUID, dict] = {}
    for row in rows:
        pid = row.product_id
        if pid not in products:
            products[pid] = {
                "product_name": row.product_name,
                "compare_mode": row.compare_mode or "none",
                "display_unit": row.base_unit or _DEFAULT_UNIT.get(row.compare_mode or "none", "ea"),
                "vendors": [],
            }
        products[pid]["vendors"].append(
            VendorPrice(
                vendor_name=row.vendor_name,
                vendor_id=str(row.vendor_id),
                avg_price_per_display_unit=float(row.avg_price) if row.avg_price else None,
                min_price_per_display_unit=float(row.min_price) if row.min_price else None,
                max_price_per_display_unit=float(row.max_price) if row.max_price else None,
                invoice_count=row.invoice_count,
                last_seen=row.last_seen,
                raw_avg_unit_price=float(row.raw_avg_unit_price) if row.raw_avg_unit_price else None,
            )
        )

    return [
        PriceComparison(
            product_name=data["product_name"],
            compare_mode=data["compare_mode"],
            display_unit=data["display_unit"],
            vendors=data["vendors"],
        )
        for data in products.values()
    ]
