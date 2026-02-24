import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.pricing import PriceComparisonOut
from app.services.pricing.compare import compare_prices

router = APIRouter()


@router.get("/pricing/compare", response_model=list[PriceComparisonOut])
def price_comparison(
    product_id: Optional[uuid.UUID] = Query(None, description="Filter by product"),
    db: Session = Depends(get_db),
):
    return compare_prices(db=db, product_id=product_id)
