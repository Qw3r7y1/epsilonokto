import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

import enum


class InvoiceStatus(str, enum.Enum):
    pending = "pending"
    processing = "processing"
    extracted = "extracted"
    failed = "failed"


class CompareMode(str, enum.Enum):
    weight = "weight"
    volume = "volume"
    count = "count"
    none = "none"


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Vendor(Base):
    __tablename__ = "vendors"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    alias: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    invoices: Mapped[list["Invoice"]] = relationship(back_populates="vendor")


class Product(Base):
    __tablename__ = "products"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    compare_mode: Mapped[CompareMode] = mapped_column(
        Enum(CompareMode), default=CompareMode.none
    )
    base_unit: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True
    )  # g, ml, ea
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    line_items: Mapped[list["InvoiceLineItem"]] = relationship(back_populates="product")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    vendor_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True
    )
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    invoice_number: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    invoice_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    total_amount: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    status: Mapped[InvoiceStatus] = mapped_column(
        Enum(InvoiceStatus), default=InvoiceStatus.pending
    )
    ocr_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_scanned: Mapped[bool] = mapped_column(Boolean, default=False)
    page_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    vendor: Mapped[Optional["Vendor"]] = relationship(back_populates="invoices")
    line_items: Mapped[list["InvoiceLineItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan"
    )


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False
    )
    product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("products.id"), nullable=True
    )

    # Raw extracted values
    raw_description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_quantity: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    raw_unit: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    raw_unit_price: Mapped[Optional[float]] = mapped_column(Numeric(12, 4), nullable=True)
    raw_total: Mapped[Optional[float]] = mapped_column(Numeric(12, 2), nullable=True)

    # Normalized values
    cases: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    units_per_case: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    unit_size: Mapped[Optional[float]] = mapped_column(Numeric(10, 4), nullable=True)
    unit_size_unit: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    total_base_quantity: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 6), nullable=True
    )  # in base_unit (g / ml / ea)
    price_per_base_unit: Mapped[Optional[float]] = mapped_column(
        Numeric(14, 6), nullable=True
    )

    line_number: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    invoice: Mapped["Invoice"] = relationship(back_populates="line_items")
    product: Mapped[Optional["Product"]] = relationship(back_populates="line_items")
