from uuid import UUID
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Product
from app.schemas.product import ProductOut, ProductCreate, ProductUpdate
from app.services.extraction.normalize import normalize_vendor_name

router = APIRouter(prefix="/products", tags=["Products"])


def _normalize(name: str) -> str:
    """Reuse the vendor name normalizer — same logic applies to products."""
    return normalize_vendor_name(name)


@router.get("/", response_model=list[ProductOut])
async def list_products(
    category: Optional[str] = Query(None, description="Filter by category"),
    compare_mode: Optional[str] = Query(None, description="Filter by compare mode"),
    db: AsyncSession = Depends(get_db),
):
    """List all products in the catalog."""
    query = select(Product).order_by(Product.name)
    if category:
        query = query.where(Product.category == category)
    if compare_mode:
        query = query.where(Product.compare_mode == compare_mode)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/", response_model=ProductOut, status_code=201)
async def create_product(
    product: ProductCreate,
    db: AsyncSession = Depends(get_db),
):
    """Add a new product to the catalog."""
    normalized = _normalize(product.name)
    existing = await db.execute(
        select(Product).where(Product.normalized_name == normalized)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=409,
            detail=f"A product with the normalized name '{normalized}' already exists.",
        )

    db_product = Product(
        name=product.name,
        normalized_name=normalized,
        category=product.category,
        compare_mode=product.compare_mode,
        base_unit=product.base_unit,
    )
    db.add(db_product)
    await db.flush()
    await db.refresh(db_product)
    return db_product


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    """Get a single product by ID."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductOut)
async def update_product(
    product_id: UUID,
    updates: ProductUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Partially update a product (compare_mode, base_unit, category, name)."""
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    if updates.name is not None:
        product.name = updates.name
        product.normalized_name = _normalize(updates.name)
    if updates.category is not None:
        product.category = updates.category
    if updates.compare_mode is not None:
        product.compare_mode = updates.compare_mode
    if updates.base_unit is not None:
        product.base_unit = updates.base_unit

    await db.flush()
    await db.refresh(product)
    return product


@router.delete("/{product_id}", status_code=204)
async def delete_product(product_id: UUID, db: AsyncSession = Depends(get_db)):
    """Remove a product from the catalog.

    Note: existing LineItem.product_id references become NULL (nullable FK).
    """
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalar_one_or_none()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    await db.delete(product)
    await db.flush()
