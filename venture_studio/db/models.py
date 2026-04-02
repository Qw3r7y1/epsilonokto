"""
Venture Studio — Database Models

Core tables:
  experiments  — opportunity → experiment lifecycle
  assets       — built digital assets (sites, tools, content)
  agents       — agent registry & runtime state
  budget_ledger — every spend/revenue event
  audit_log    — immutable governance trail
  strategies   — reusable playbooks from successful experiments
  outcomes     — per-experiment metric snapshots
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from venture_studio.db.session import Base


# ── Enums ────────────────────────────────────────────────────────────────────


class ExperimentStatus(str, enum.Enum):
    discovered = "discovered"
    scoring = "scoring"
    validated = "validated"
    building = "building"
    published = "published"
    distributing = "distributing"
    monitoring = "monitoring"
    winning = "winning"
    killed = "killed"
    archived = "archived"


class AgentStatus(str, enum.Enum):
    idle = "idle"
    running = "running"
    paused = "paused"
    errored = "errored"
    disabled = "disabled"


class LedgerEntryType(str, enum.Enum):
    spend = "spend"
    revenue = "revenue"
    refund = "refund"
    allocation = "allocation"


class AssetType(str, enum.Enum):
    website = "website"
    landing_page = "landing_page"
    blog_post = "blog_post"
    tool = "tool"
    email_sequence = "email_sequence"
    video = "video"
    social_post = "social_post"
    product = "product"


class PodType(str, enum.Enum):
    affiliate = "affiliate"
    digital_product = "digital_product"
    lead_gen = "lead_gen"
    micro_saas = "micro_saas"
    trend_media = "trend_media"


# ── Helper ───────────────────────────────────────────────────────────────────


def _uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )


def _now() -> Mapped[datetime]:
    return mapped_column(DateTime(timezone=True), server_default=func.now())


# ── Models ───────────────────────────────────────────────────────────────────


class Experiment(Base):
    __tablename__ = "vs_experiments"

    id: Mapped[uuid.UUID] = _uuid_pk()
    title: Mapped[str] = mapped_column(String(512))
    niche: Mapped[str] = mapped_column(String(256))
    pod: Mapped[PodType] = mapped_column(Enum(PodType), default=PodType.affiliate)
    status: Mapped[ExperimentStatus] = mapped_column(
        Enum(ExperimentStatus), default=ExperimentStatus.discovered
    )
    score: Mapped[float | None] = mapped_column(Float, nullable=True)
    hypothesis: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_: Mapped[dict | None] = mapped_column("metadata", JSONB, nullable=True)

    budget_allocated: Mapped[float] = mapped_column(Float, default=0.0)
    budget_spent: Mapped[float] = mapped_column(Float, default=0.0)
    revenue_total: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = _now()
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # relationships
    assets: Mapped[list[Asset]] = relationship(back_populates="experiment", cascade="all, delete-orphan")
    outcomes: Mapped[list[Outcome]] = relationship(back_populates="experiment", cascade="all, delete-orphan")
    ledger_entries: Mapped[list[BudgetLedger]] = relationship(back_populates="experiment")

    __table_args__ = (
        Index("ix_vs_exp_status", "status"),
        Index("ix_vs_exp_pod", "pod"),
    )


class Asset(Base):
    __tablename__ = "vs_assets"

    id: Mapped[uuid.UUID] = _uuid_pk()
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vs_experiments.id", ondelete="CASCADE")
    )
    asset_type: Mapped[AssetType] = mapped_column(Enum(AssetType))
    name: Mapped[str] = mapped_column(String(512))
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    storage_key: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    content: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    is_live: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = _now()

    experiment: Mapped[Experiment] = relationship(back_populates="assets")

    __table_args__ = (
        Index("ix_vs_asset_exp", "experiment_id"),
    )


class Agent(Base):
    __tablename__ = "vs_agents"

    id: Mapped[uuid.UUID] = _uuid_pk()
    name: Mapped[str] = mapped_column(String(128), unique=True)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.idle)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)

    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    total_successes: Mapped[int] = mapped_column(Integer, default=0)
    total_failures: Mapped[int] = mapped_column(Integer, default=0)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = _now()


class BudgetLedger(Base):
    __tablename__ = "vs_budget_ledger"

    id: Mapped[uuid.UUID] = _uuid_pk()
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vs_experiments.id", ondelete="SET NULL"), nullable=True
    )
    entry_type: Mapped[LedgerEntryType] = mapped_column(Enum(LedgerEntryType))
    amount_usd: Mapped[float] = mapped_column(Float)
    category: Mapped[str] = mapped_column(String(128))  # e.g. "claude_api", "serpapi", "hosting"
    description: Mapped[str] = mapped_column(Text, default="")
    agent_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = _now()

    experiment: Mapped[Experiment | None] = relationship(back_populates="ledger_entries")

    __table_args__ = (
        Index("ix_vs_ledger_exp", "experiment_id"),
        Index("ix_vs_ledger_type", "entry_type"),
        Index("ix_vs_ledger_created", "created_at"),
    )


class AuditLog(Base):
    __tablename__ = "vs_audit_log"

    id: Mapped[uuid.UUID] = _uuid_pk()
    agent_name: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(256))
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vs_experiments.id", ondelete="SET NULL"), nullable=True
    )
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        Index("ix_vs_audit_agent", "agent_name"),
        Index("ix_vs_audit_created", "created_at"),
    )


class Outcome(Base):
    __tablename__ = "vs_outcomes"

    id: Mapped[uuid.UUID] = _uuid_pk()
    experiment_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vs_experiments.id", ondelete="CASCADE")
    )
    day: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)
    revenue_usd: Mapped[float] = mapped_column(Float, default=0.0)
    spend_usd: Mapped[float] = mapped_column(Float, default=0.0)
    metrics: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = _now()

    experiment: Mapped[Experiment] = relationship(back_populates="outcomes")

    __table_args__ = (
        Index("ix_vs_outcome_exp_day", "experiment_id", "day"),
    )


class Strategy(Base):
    __tablename__ = "vs_strategies"

    id: Mapped[uuid.UUID] = _uuid_pk()
    experiment_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("vs_experiments.id", ondelete="SET NULL"), nullable=True
    )
    title: Mapped[str] = mapped_column(String(512))
    pod: Mapped[PodType] = mapped_column(Enum(PodType))
    niche: Mapped[str] = mapped_column(String(256))
    playbook: Mapped[dict] = mapped_column(JSONB)  # structured steps
    roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    reuse_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = _now()

    __table_args__ = (
        Index("ix_vs_strategy_pod", "pod"),
        Index("ix_vs_strategy_roi", "roi"),
    )
