"""API routes for governance, budget, and audit."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func as sqlfunc, select
from sqlalchemy.ext.asyncio import AsyncSession

from venture_studio.core.config import get_settings
from venture_studio.db.models import (
    Agent as AgentModel,
    AuditLog,
    BudgetLedger,
    LedgerEntryType,
)
from venture_studio.db.session import get_db
from venture_studio.schemas.governance import (
    AuditLogOut,
    BudgetSummary,
    GovernanceStatus,
    LedgerEntryCreate,
    LedgerEntryOut,
)

router = APIRouter(prefix="/governance", tags=["governance"])


@router.get("/status", response_model=GovernanceStatus)
async def governance_status(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    result = await db.execute(select(AgentModel))
    agents = result.scalars().all()
    agents_enabled = {a.name: a.enabled for a in agents}
    return GovernanceStatus(
        kill_switch=settings.global_kill_switch,
        active_pod=settings.active_pod,
        max_daily_spend=settings.max_daily_spend_usd,
        max_experiment_spend=settings.max_experiment_spend_usd,
        max_concurrent_experiments=settings.max_concurrent_experiments,
        circuit_breaker_threshold=settings.circuit_breaker_threshold,
        agents_enabled=agents_enabled,
    )


@router.get("/budget", response_model=BudgetSummary)
async def budget_summary(db: AsyncSession = Depends(get_db)):
    settings = get_settings()
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    spend_q = await db.execute(
        select(sqlfunc.coalesce(sqlfunc.sum(BudgetLedger.amount_usd), 0.0)).where(
            BudgetLedger.entry_type == LedgerEntryType.spend
        )
    )
    total_spend = spend_q.scalar_one()

    rev_q = await db.execute(
        select(sqlfunc.coalesce(sqlfunc.sum(BudgetLedger.amount_usd), 0.0)).where(
            BudgetLedger.entry_type == LedgerEntryType.revenue
        )
    )
    total_revenue = rev_q.scalar_one()

    daily_q = await db.execute(
        select(sqlfunc.coalesce(sqlfunc.sum(BudgetLedger.amount_usd), 0.0)).where(
            BudgetLedger.entry_type == LedgerEntryType.spend,
            BudgetLedger.created_at >= today_start,
        )
    )
    daily_spend = daily_q.scalar_one()

    return BudgetSummary(
        total_spend=total_spend,
        total_revenue=total_revenue,
        net=total_revenue - total_spend,
        daily_spend=daily_spend,
        daily_limit=settings.max_daily_spend_usd,
        budget_utilization_pct=round(daily_spend / settings.max_daily_spend_usd * 100, 1) if settings.max_daily_spend_usd > 0 else 0,
    )


@router.get("/ledger", response_model=list[LedgerEntryOut])
async def list_ledger(
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(BudgetLedger).order_by(BudgetLedger.created_at.desc()).offset(offset).limit(limit)
    )
    return result.scalars().all()


@router.post("/ledger", response_model=LedgerEntryOut, status_code=201)
async def create_ledger_entry(body: LedgerEntryCreate, db: AsyncSession = Depends(get_db)):
    entry = BudgetLedger(**body.model_dump(exclude_none=True))
    db.add(entry)
    await db.commit()
    await db.refresh(entry)
    return entry


@router.get("/audit", response_model=list[AuditLogOut])
async def list_audit_logs(
    agent_name: str | None = None,
    limit: int = Query(100, le=500),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog).order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    if agent_name:
        q = q.where(AuditLog.agent_name == agent_name)
    result = await db.execute(q)
    return result.scalars().all()
