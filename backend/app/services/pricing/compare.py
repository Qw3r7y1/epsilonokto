"""Vendor price comparison across invoice line items."""

import uuid
from typing import Optional

from sqlalchemy.orm import Session

from app.db.models import Invoice, InvoiceLineItem, Product, Vendor
from app.schemas.pricing import PriceComparisonOut, VendorPricePoint


def compare_prices(
    db: Session,
    product_id: Optional[uuid.UUID] = None,
) -> list[PriceComparisonOut]:
    q = (
        db.query(InvoiceLineItem, Invoice, Vendor, Product)
        .join(Invoice, InvoiceLineItem.invoice_id == Invoice.id)
        .join(Vendor, Invoice.vendor_id == Vendor.id)
        .join(Product, InvoiceLineItem.product_id == Product.id)
        .filter(InvoiceLineItem.product_id.isnot(None))
        .filter(Invoice.vendor_id.isnot(None))
    )

    if product_id:
        q = q.filter(InvoiceLineItem.product_id == product_id)

    rows = q.order_by(Product.id, Invoice.invoice_date.desc()).all()

    # Group by product
    products: dict[uuid.UUID, dict] = {}
    for item, invoice, vendor, product in rows:
        pid = product.id
        if pid not in products:
            products[pid] = {
                "product": product,
                "vendors": [],
            }
        products[pid]["vendors"].append(
            VendorPricePoint(
                vendor_id=vendor.id,
                vendor_name=vendor.name,
                invoice_id=invoice.id,
                invoice_date=(
                    invoice.invoice_date.date().isoformat()
                    if invoice.invoice_date
                    else None
                ),
                raw_quantity=item.raw_quantity,
                raw_unit_price=float(item.raw_unit_price) if item.raw_unit_price else None,
                total_base_quantity=(
                    float(item.total_base_quantity) if item.total_base_quantity else None
                ),
                price_per_base_unit=(
                    float(item.price_per_base_unit) if item.price_per_base_unit else None
                ),
                base_unit=product.base_unit,
            )
        )

    return [
        PriceComparisonOut(
            product_id=data["product"].id,
            product_name=data["product"].name,
            compare_mode=data["product"].compare_mode.value,
            base_unit=data["product"].base_unit,
            vendors=data["vendors"],
        )
        for data in products.values()
    ]
