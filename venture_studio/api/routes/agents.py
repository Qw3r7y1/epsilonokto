"""API routes for agents."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from venture_studio.db.models import Agent as AgentModel
from venture_studio.db.session import get_db
from venture_studio.schemas.agents import AgentOut, AgentToggle

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/", response_model=list[AgentOut])
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentModel).order_by(AgentModel.name))
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentOut)
async def get_agent(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent


@router.patch("/{agent_id}/toggle", response_model=AgentOut)
async def toggle_agent(
    agent_id: uuid.UUID,
    body: AgentToggle,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    agent.enabled = body.enabled
    await db.commit()
    await db.refresh(agent)
    return agent


@router.post("/{agent_id}/reset-circuit-breaker", response_model=AgentOut)
async def reset_circuit_breaker(agent_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AgentModel).where(AgentModel.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    agent.consecutive_failures = 0
    from venture_studio.db.models import AgentStatus
    agent.status = AgentStatus.idle
    await db.commit()
    await db.refresh(agent)
    return agent
