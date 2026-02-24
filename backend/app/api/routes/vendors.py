import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.models import Vendor
from app.db.session import get_db
from app.schemas.vendor import VendorCreate, VendorOut, VendorUpdate

router = APIRouter()


@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(db: Session = Depends(get_db)):
    return db.query(Vendor).order_by(Vendor.name).all()


@router.post("/vendors", response_model=VendorOut, status_code=201)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db)):
    existing = db.query(Vendor).filter(Vendor.name == payload.name).first()
    if existing:
        raise HTTPException(status_code=409, detail="Vendor with this name already exists")
    vendor = Vendor(**payload.model_dump())
    db.add(vendor)
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/vendors/{vendor_id}", response_model=VendorOut)
def get_vendor(vendor_id: uuid.UUID, db: Session = Depends(get_db)):
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    return vendor


@router.patch("/vendors/{vendor_id}", response_model=VendorOut)
def update_vendor(
    vendor_id: uuid.UUID, payload: VendorUpdate, db: Session = Depends(get_db)
):
    vendor = db.get(Vendor, vendor_id)
    if not vendor:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    db.commit()
    db.refresh(vendor)
    return vendor
