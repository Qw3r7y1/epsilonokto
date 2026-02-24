import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class VendorBase(BaseModel):
    name: str
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class VendorCreate(VendorBase):
    pass


class VendorUpdate(BaseModel):
    name: Optional[str] = None
    contact_email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    notes: Optional[str] = None


class VendorOut(VendorBase):
    id: uuid.UUID
    normalized_name: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
