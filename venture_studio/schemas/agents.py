"""Pydantic schemas for agents."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel

from venture_studio.db.models import AgentStatus


class AgentOut(BaseModel):
    id: uuid.UUID
    name: str
    description: str
    status: AgentStatus
    enabled: bool
    consecutive_failures: int
    total_runs: int
    total_successes: int
    total_failures: int
    last_run_at: datetime | None

    model_config = {"from_attributes": True}


class AgentToggle(BaseModel):
    enabled: bool
