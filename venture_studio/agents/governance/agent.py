"""
Governance Controller Agent

Layer 1 — Command.
Monitors system health, enforces policies, manages circuit breakers,
and performs safety audits.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func as sqlfunc, select

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.db.models import (
    Agent as AgentModel,
    AgentStatus,
    AuditLog,
    BudgetLedger,
    Experiment,
    ExperimentStatus,
    LedgerEntryType,
)


class GovernanceAgent(BaseAgent):
    name = "governance_controller"
    description = "Monitors system health and enforces governance policies"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        report: dict[str, Any] = {}

        # 1. Budget audit
        report["budget"] = await self._audit_budget()

        # 2. Agent health check
        report["agent_health"] = await self._check_agent_health()

        # 3. Experiment compliance
        report["experiment_compliance"] = await self._check_experiments()

        # 4. Reset circuit breakers if requested
        if context.get("reset_circuit_breakers"):
            report["circuit_breaker_resets"] = await self._reset_circuit_breakers(
                context.get("agent_names", [])
            )

        # 5. Content compliance check
        report["content_flags"] = await self._check_content_compliance()

        return AgentResult(success=True, data=report)

    async def _audit_budget(self) -> dict:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

        # Daily spend
        result = await self.db.execute(
            select(sqlfunc.coalesce(sqlfunc.sum(BudgetLedger.amount_usd), 0.0)).where(
                BudgetLedger.entry_type == LedgerEntryType.spend,
                BudgetLedger.created_at >= today_start,
            )
        )
        daily_spend = result.scalar_one()

        # Total spend
        result = await self.db.execute(
            select(sqlfunc.coalesce(sqlfunc.sum(BudgetLedger.amount_usd), 0.0)).where(
                BudgetLedger.entry_type == LedgerEntryType.spend,
            )
        )
        total_spend = result.scalar_one()

        # Total revenue
        result = await self.db.execute(
            select(sqlfunc.coalesce(sqlfunc.sum(BudgetLedger.amount_usd), 0.0)).where(
                BudgetLedger.entry_type == LedgerEntryType.revenue,
            )
        )
        total_revenue = result.scalar_one()

        return {
            "daily_spend": daily_spend,
            "daily_limit": self.settings.max_daily_spend_usd,
            "daily_utilization_pct": round(daily_spend / self.settings.max_daily_spend_usd * 100, 1),
            "total_spend": total_spend,
            "total_revenue": total_revenue,
            "net_profit": total_revenue - total_spend,
        }

    async def _check_agent_health(self) -> list[dict]:
        result = await self.db.execute(select(AgentModel))
        agents = result.scalars().all()

        issues = []
        for agent in agents:
            if agent.consecutive_failures >= self.settings.circuit_breaker_threshold:
                issues.append({
                    "agent": agent.name,
                    "issue": "circuit_breaker_open",
                    "failures": agent.consecutive_failures,
                })
            if agent.status == AgentStatus.errored:
                issues.append({
                    "agent": agent.name,
                    "issue": "errored_state",
                })
        return issues

    async def _check_experiments(self) -> dict:
        result = await self.db.execute(
            select(Experiment).where(
                Experiment.status.notin_([ExperimentStatus.killed, ExperimentStatus.archived])
            )
        )
        experiments = result.scalars().all()

        over_budget = []
        for exp in experiments:
            if exp.budget_spent > self.settings.max_experiment_spend_usd:
                over_budget.append({
                    "experiment_id": str(exp.id),
                    "title": exp.title,
                    "budget_spent": exp.budget_spent,
                    "limit": self.settings.max_experiment_spend_usd,
                })

        return {
            "active_count": len(experiments),
            "max_concurrent": self.settings.max_concurrent_experiments,
            "over_budget": over_budget,
        }

    async def _reset_circuit_breakers(self, agent_names: list[str]) -> list[str]:
        reset = []
        for name in agent_names:
            result = await self.db.execute(
                select(AgentModel).where(AgentModel.name == name)
            )
            agent = result.scalar_one_or_none()
            if agent:
                agent.consecutive_failures = 0
                agent.status = AgentStatus.idle
                reset.append(name)
        return reset

    async def _check_content_compliance(self) -> list[str]:
        """Placeholder for content compliance scanning."""
        # Future: scan published assets for prohibited content
        return []
