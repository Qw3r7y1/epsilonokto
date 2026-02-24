"""Vendor price comparison across invoice line items."""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Invoice, LineItem, Product, Vendor
from app.schemas.pricing import PriceComparisonOut, VendorPricePoint


async def compare_prices(
    db: AsyncSession,
    product_id: Optional[uuid.UUID] = None,
) -> list[PriceComparisonOut]:
    q = (
        select(LineItem, Invoice, Vendor, Product)
        .join(Invoice, LineItem.invoice_id == Invoice.id)
        .join(Vendor, Invoice.vendor_id == Vendor.id)
        .join(Product, LineItem.product_id == Product.id)
        .where(LineItem.product_id.isnot(None))
        .where(Invoice.vendor_id.isnot(None))
    )

    if product_id:
        q = q.where(LineItem.product_id == product_id)

    q = q.order_by(Product.id, Invoice.invoice_date.desc())
    result = await db.execute(q)
    rows = result.all()

    # Group by product
    products: dict[uuid.UUID, dict] = {}
    for row in rows:
        item, invoice, vendor, product = row
        pid = product.id
        if pid not in products:
            products[pid] = {"product": product, "vendors": []}
        products[pid]["vendors"].append(
            VendorPricePoint(
                vendor_id=vendor.id,
                vendor_name=vendor.name,
                invoice_id=invoice.id,
                invoice_date=(
                    invoice.invoice_date.isoformat() if invoice.invoice_date else None
                ),
                raw_quantity=item.raw_quantity_text,
                raw_unit_price=float(item.unit_price) if item.unit_price else None,
                total_base_quantity=(
                    float(item.normalized_quantity) if item.normalized_quantity else None
                ),
                price_per_base_unit=(
                    float(item.normalized_unit_price) if item.normalized_unit_price else None
                ),
                base_unit=product.base_unit,
            )
        )

    return [
        PriceComparisonOut(
            product_id=data["product"].id,
            product_name=data["product"].name,
            compare_mode=data["product"].compare_mode,
            base_unit=data["product"].base_unit,
            vendors=data["vendors"],
        )
        for data in products.values()
    ]
