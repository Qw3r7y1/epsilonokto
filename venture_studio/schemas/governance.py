"""Pydantic schemas for governance & budget."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from venture_studio.db.models import LedgerEntryType


class LedgerEntryCreate(BaseModel):
    experiment_id: uuid.UUID | None = None
    entry_type: LedgerEntryType
    amount_usd: float
    category: str
    description: str = ""
    agent_name: str | None = None


class LedgerEntryOut(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID | None
    entry_type: LedgerEntryType
    amount_usd: float
    category: str
    description: str
    agent_name: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class BudgetSummary(BaseModel):
    total_spend: float
    total_revenue: float
    net: float
    daily_spend: float
    daily_limit: float
    budget_utilization_pct: float


class GovernanceStatus(BaseModel):
    kill_switch: bool
    active_pod: str
    max_daily_spend: float
    max_experiment_spend: float
    max_concurrent_experiments: int
    circuit_breaker_threshold: int
    agents_enabled: dict[str, bool]


class AuditLogOut(BaseModel):
    id: uuid.UUID
    agent_name: str
    action: str
    experiment_id: uuid.UUID | None
    details: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}
