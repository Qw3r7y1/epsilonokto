"""
Capital Allocator Agent

Layer 6 — Finance & Analytics.
Analyzes ROI across experiments and reallocates budget to winners.
Implements multi-armed bandit with risk-adjusted scoring.

Skills mastered: Thompson sampling, ROI calculation, risk-adjusted returns,
portfolio rebalancing, exploration vs exploitation, time-based kill thresholds.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func as sqlfunc, select

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.db.models import (
    BudgetLedger,
    Experiment,
    ExperimentStatus,
    LedgerEntryType,
)


class CapitalAllocator(BaseAgent):
    name = "capital_allocator"
    description = "Allocates capital with risk-adjusted scoring and time-based kill thresholds"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        total_budget = context.get("total_budget", self.settings.max_daily_spend_usd)

        # Step 1: Get active experiments with financials
        experiments = await self._get_experiment_financials()

        if not experiments:
            return AgentResult(success=True, data={"message": "No active experiments", "allocations": []})

        # Step 2: Score experiments with risk-adjusted ROI
        scored = self._score_experiments(experiments)

        # Step 3: Allocate using Thompson-inspired weighting
        allocations = self._allocate(scored, total_budget)

        # Step 4: Update experiment budgets
        for alloc in allocations:
            result = await self.db.execute(
                select(Experiment).where(Experiment.id == alloc["experiment_id"])
            )
            exp = result.scalar_one_or_none()
            if exp:
                exp.budget_allocated = alloc["allocated_budget"]

            # Record allocation in ledger
            self.db.add(BudgetLedger(
                experiment_id=alloc["experiment_id"],
                entry_type=LedgerEntryType.allocation,
                amount_usd=alloc["allocated_budget"],
                category="capital_allocation",
                description=f"Budget allocation: ROI score {alloc['roi_score']:.2f}, risk-adjusted",
                agent_name=self.name,
            ))

        # Step 5: Kill underperformers with graduated time-based thresholds
        killed = await self._kill_underperformers(scored)

        return AgentResult(
            success=True,
            data={
                "allocations": allocations,
                "killed_experiments": killed,
                "total_allocated": sum(a["allocated_budget"] for a in allocations),
            },
        )

    async def _get_experiment_financials(self) -> list[dict]:
        active_statuses = [
            ExperimentStatus.published,
            ExperimentStatus.distributing,
            ExperimentStatus.monitoring,
            ExperimentStatus.winning,
        ]
        result = await self.db.execute(
            select(Experiment).where(Experiment.status.in_(active_statuses))
        )
        experiments = result.scalars().all()

        now = datetime.now(timezone.utc)
        financials = []
        for exp in experiments:
            days_active = (now - exp.created_at.replace(tzinfo=timezone.utc)).days if exp.created_at else 0
            financials.append({
                "experiment_id": exp.id,
                "title": exp.title,
                "status": exp.status.value,
                "budget_spent": exp.budget_spent,
                "revenue_total": exp.revenue_total,
                "roi": (exp.revenue_total / exp.budget_spent - 1) if exp.budget_spent > 0 else 0.0,
                "days_active": max(days_active, 1),
            })
        return financials

    def _score_experiments(self, experiments: list[dict]) -> list[dict]:
        for exp in experiments:
            roi = exp["roi"]
            spend = exp["budget_spent"]
            days = exp["days_active"]

            if spend < 1.0:
                # Exploration bonus for new experiments — give them a chance
                exp["roi_score"] = 0.5
            elif roi > 0:
                # Risk-adjusted scoring: penalize high variance (high spend, low revenue consistency)
                volatility_proxy = spend / max(exp["revenue_total"], 0.01)
                risk_adjusted_roi = roi / (1 + volatility_proxy * 0.1)
                exp["roi_score"] = min(risk_adjusted_roi, 10.0) / 10.0
            else:
                # Negative ROI — score relative to how negative, but consider age
                # Newer experiments get more patience
                age_factor = min(days / 14.0, 1.0)  # Full penalty after 14 days
                exp["roi_score"] = max(roi * age_factor, -1.0) / 10.0

        return sorted(experiments, key=lambda e: e["roi_score"], reverse=True)

    def _allocate(self, scored: list[dict], total_budget: float) -> list[dict]:
        """Proportional allocation weighted by ROI score."""
        min_score = min(e["roi_score"] for e in scored)
        shifted = [e["roi_score"] - min_score + 0.1 for e in scored]
        total_weight = sum(shifted)

        allocations = []
        for exp, weight in zip(scored, shifted):
            share = weight / total_weight
            allocated = round(total_budget * share, 2)
            allocations.append({
                "experiment_id": exp["experiment_id"],
                "title": exp["title"],
                "roi_score": exp["roi_score"],
                "allocated_budget": allocated,
                "share_pct": round(share * 100, 1),
            })
        return allocations

    async def _kill_underperformers(self, scored: list[dict]) -> list[str]:
        """Kill experiments using graduated time-based thresholds.

        - ROI < -0.8 after 3+ days and spend > $10: kill immediately
        - ROI < -0.5 after 7+ days and spend > $10: kill
        - ROI < -0.3 after 14+ days and spend > $10: kill
        """
        killed = []
        for exp in scored:
            roi = exp["roi"]
            days = exp["days_active"]
            spend = exp["budget_spent"]

            if spend <= 10.0:
                continue  # Minimum viable test budget not reached

            should_kill = (
                (roi < -0.8 and days >= 3)
                or (roi < -0.5 and days >= 7)
                or (roi < -0.3 and days >= 14)
            )

            if should_kill:
                result = await self.db.execute(
                    select(Experiment).where(Experiment.id == exp["experiment_id"])
                )
                experiment = result.scalar_one_or_none()
                if experiment:
                    experiment.status = ExperimentStatus.killed
                    killed.append(exp["title"])
        return killed
