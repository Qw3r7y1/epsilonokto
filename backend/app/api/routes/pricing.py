from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.vendor import PriceComparison
from app.schemas.pricing import PriceHistoryEntry
from app.services.pricing.compare import compare_product_prices, get_price_history

router = APIRouter(prefix="/pricing", tags=["Pricing"])


@router.get("/compare", response_model=list[PriceComparison])
async def price_comparison(
    product_name: str | None = Query(None, description="Filter by product name"),
    category: str | None = Query(None, description="Filter by product category"),
    vendor_id: str | None = Query(None, description="Filter by vendor ID"),
    db: AsyncSession = Depends(get_db),
):
    """Compare normalized prices for products across all vendors.

    Results are grouped by product.  Each product shows one entry per vendor
    with avg/min/max price expressed in the product's configured display unit
    (e.g. price/lb for weight products, price/L for volume products).
    """
    return await compare_product_prices(
        db=db,
        product_name=product_name,
        category=category,
        vendor_id=vendor_id,
    )


@router.get("/history/{product_id}", response_model=list[PriceHistoryEntry])
async def price_history(
    product_id: str,
    vendor_id: str | None = Query(None, description="Filter by vendor ID"),
    db: AsyncSession = Depends(get_db),
):
    """Return the price history for a specific product over time."""
    return await get_price_history(db=db, product_id=product_id, vendor_id=vendor_id)
