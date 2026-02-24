import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Vendor
from app.db.session import get_db
from app.schemas.vendor import VendorCreate, VendorOut, VendorUpdate

router = APIRouter()


@router.get("/vendors", response_model=list[VendorOut])
async def list_vendors(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).order_by(Vendor.name))
    return result.scalars().all()


@router.post("/vendors", response_model=VendorOut, status_code=201)
async def create_vendor(payload: VendorCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).where(Vendor.name == payload.name))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Vendor with this name already exists")
    vendor = Vendor(
        **payload.model_dump(),
        normalized_name=payload.name.strip().lower(),
    )
    db.add(vendor)
    await db.flush()
    await db.refresh(vendor)
    return vendor


@router.get("/vendors/{vendor_id}", response_model=VendorOut)
async def get_vendor(vendor_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    vendor = await db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.patch("/vendors/{vendor_id}", response_model=VendorOut)
async def update_vendor(
    vendor_id: uuid.UUID, payload: VendorUpdate, db: AsyncSession = Depends(get_db)
):
    vendor = await db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(vendor, field, value)
    if "name" in updates:
        vendor.normalized_name = updates["name"].strip().lower()
    await db.flush()
    await db.refresh(vendor)
    return vendor
