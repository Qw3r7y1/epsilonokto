import uuid
from datetime import date, datetime

from sqlalchemy import (
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.db.session import Base


class Vendor(Base):
    __tablename__ = "vendors"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, unique=True)
    normalized_name = Column(String(255), nullable=False, index=True)
    contact_email = Column(String(255))
    phone = Column(String(50))
    address = Column(Text)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    invoices = relationship("Invoice", back_populates="vendor")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vendor_id = Column(UUID(as_uuid=True), ForeignKey("vendors.id"), nullable=True)

    # Source file
    original_filename = Column(String(500), nullable=False)
    stored_path = Column(String(1000), nullable=False)
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 for dedup
    file_type = Column(String(20))  # pdf, png, jpg, etc.

    # Extracted fields
    invoice_number = Column(String(100), index=True)
    invoice_date = Column(Date)
    due_date = Column(Date)
    subtotal = Column(Numeric(12, 2))
    tax = Column(Numeric(12, 2))
    total = Column(Numeric(12, 2))
    currency = Column(String(3), default="USD")

    # Raw extracted text (for debugging / re-extraction)
    raw_text = Column(Text)

    # Processing status
    status = Column(String(20), default="pending")  # pending, processed, failed, review
    extraction_confidence = Column(Numeric(5, 2))  # 0-100

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    vendor = relationship("Vendor", back_populates="invoices")
    line_items = relationship("LineItem", back_populates="invoice", cascade="all, delete-orphan")


class Product(Base):
    __tablename__ = "products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    normalized_name = Column(String(255), nullable=False, index=True)
    category = Column(String(100))

    # How to compare prices for this product across vendors
    # "weight" → normalize to grams then compare per-gram price
    # "volume" → normalize to ml then compare per-ml price
    # "count"  → compare per-unit price (cases, each, packs)
    # "none"   → don't normalize, show raw units side by side
    compare_mode = Column(String(20), default="none")

    # The canonical unit for display after normalization (e.g., "kg", "oz", "L")
    # If null, system picks a sensible default per compare_mode
    base_unit = Column(String(20), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (UniqueConstraint("normalized_name", name="uq_product_name"),)


class LineItem(Base):
    __tablename__ = "line_items"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    invoice_id = Column(UUID(as_uuid=True), ForeignKey("invoices.id"), nullable=False)
    product_id = Column(UUID(as_uuid=True), ForeignKey("products.id"), nullable=True)

    description = Column(Text, nullable=False)

    # ── Raw quantity as it appears on the invoice ────────
    # For "5/20" format: cases=5, units_per_case=20, raw_quantity=100
    # For simple "10 lb":  cases=null, units_per_case=null, raw_quantity=10
    raw_quantity_text = Column(String(50))     # original text, e.g. "5/20", "10", "3x24"
    cases = Column(Numeric(10, 3))             # number of cases/packs (null if simple qty)
    units_per_case = Column(Numeric(10, 3))    # units inside each case (null if simple qty)
    raw_quantity = Column(Numeric(12, 3))       # total quantity = cases * units_per_case, or direct
    raw_unit = Column(String(50))              # unit as written: "oz", "lb", "g", "cs", "ea", "gal"

    # ── Normalized for comparison ────────────────────────
    # Converted to a base unit (grams for weight, ml for volume, units for count)
    normalized_quantity = Column(Numeric(14, 4))  # quantity in base unit
    normalized_unit = Column(String(20))          # "g", "ml", or "ea"

    # ── Pricing ──────────────────────────────────────────
    unit_price = Column(Numeric(12, 4))          # price per raw_unit
    total_price = Column(Numeric(12, 2))         # line total
    normalized_unit_price = Column(Numeric(14, 6))  # price per normalized unit (for comparison)

    position = Column(Integer)  # row order on the invoice

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    invoice = relationship("Invoice", back_populates="line_items")
    product = relationship("Product")
