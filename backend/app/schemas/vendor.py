import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr


class VendorBase(BaseModel):
    name: str
    alias: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    alias: Optional[str] = None
    contact_email: Optional[str] = None
    notes: Optional[str] = None


class VendorOut(VendorBase):
    id: uuid.UUID
    created_at: datetime

    model_config = {"from_attributes": True}
