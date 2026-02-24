from datetime import datetime
from uuid import UUID
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict

CompareModeType = Literal["weight", "volume", "count", "none"]


class ProductBase(BaseModel):
    name: str
    category: Optional[str] = None
    compare_mode: CompareModeType = "none"
    base_unit: Optional[str] = None


class ProductCreate(ProductBase):
    pass


class ProductUpdate(BaseModel):
    """All fields optional for PATCH semantics."""
    name: Optional[str] = None
    category: Optional[str] = None
    compare_mode: Optional[CompareModeType] = None
    base_unit: Optional[str] = None


class ProductOut(ProductBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    normalized_name: str
    created_at: datetime
