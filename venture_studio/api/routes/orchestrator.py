"""API routes for orchestrator actions."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from venture_studio.db.session import get_db
from venture_studio.services.orchestrator import Orchestrator

router = APIRouter(prefix="/orchestrator", tags=["orchestrator"])


@router.post("/discover")
async def trigger_discovery(db: AsyncSession = Depends(get_db)):
    """Trigger a discovery cycle to find new opportunities."""
    orch = Orchestrator(db)
    return await orch.run_discovery_cycle()


@router.post("/governance-check")
async def trigger_governance_check(db: AsyncSession = Depends(get_db)):
    """Run a governance health check."""
    orch = Orchestrator(db)
    return await orch.run_governance_check()


@router.post("/recursive-improvement")
async def trigger_recursive_improvement(db: AsyncSession = Depends(get_db)):
    """Run the Agent Architect to propose and create new agents."""
    orch = Orchestrator(db)
    return await orch.run_recursive_improvement()
