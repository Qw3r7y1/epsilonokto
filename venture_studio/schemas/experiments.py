"""Pydantic schemas for experiments."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from venture_studio.db.models import ExperimentStatus, PodType


class ExperimentCreate(BaseModel):
    title: str = Field(..., max_length=512)
    niche: str = Field(..., max_length=256)
    pod: PodType = PodType.affiliate
    hypothesis: str | None = None
    metadata_: dict | None = Field(None, alias="metadata")


class ExperimentUpdate(BaseModel):
    status: ExperimentStatus | None = None
    score: float | None = None
    hypothesis: str | None = None
    budget_allocated: float | None = None


class ExperimentOut(BaseModel):
    id: uuid.UUID
    title: str
    niche: str
    pod: PodType
    status: ExperimentStatus
    score: float | None
    hypothesis: str | None
    budget_allocated: float
    budget_spent: float
    revenue_total: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OutcomeOut(BaseModel):
    id: uuid.UUID
    experiment_id: uuid.UUID
    day: datetime
    impressions: int
    clicks: int
    conversions: int
    revenue_usd: float
    spend_usd: float
    metrics: dict | None

    model_config = {"from_attributes": True}
