from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.models import Vendor
from app.schemas.vendor import VendorOut, VendorCreate
from app.services.extraction.normalize import normalize_vendor_name

router = APIRouter(prefix="/vendors", tags=["Vendors"])


@router.get("/", response_model=list[VendorOut])
async def list_vendors(db: AsyncSession = Depends(get_db)):
    """List all vendors."""
    result = await db.execute(select(Vendor).order_by(Vendor.name))
    return result.scalars().all()


@router.post("/", response_model=VendorOut, status_code=201)
async def create_vendor(
    vendor: VendorCreate,
    db: AsyncSession = Depends(get_db),
):
    """Manually create a vendor."""
    db_vendor = Vendor(
        name=vendor.name,
        normalized_name=normalize_vendor_name(vendor.name),
        contact_email=vendor.contact_email,
        phone=vendor.phone,
        address=vendor.address,
        notes=vendor.notes,
    )
    db.add(db_vendor)
    await db.flush()
    await db.refresh(db_vendor)
    return db_vendor


@router.get("/{vendor_id}", response_model=VendorOut)
async def get_vendor(vendor_id: UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalar_one_or_none()
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor
