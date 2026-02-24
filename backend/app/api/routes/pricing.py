import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.vendor import PriceComparison
from app.services.pricing.compare import compare_prices

router = APIRouter()


@router.get("/pricing/compare", response_model=list[PriceComparison])
async def price_comparison(
    product_id: Optional[uuid.UUID] = Query(None, description="Filter by product"),
    db: AsyncSession = Depends(get_db),
):
    return await compare_prices(db=db, product_id=product_id)
