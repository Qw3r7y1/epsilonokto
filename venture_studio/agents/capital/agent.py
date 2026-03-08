"""
Capital Allocator Agent

Layer 6 — Finance & Analytics.
Analyzes ROI across experiments and reallocates budget to winners.
Implements a multi-armed bandit approach with Thompson Sampling.
"""

from __future__ import annotations

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
    description = "Allocates capital to winning experiments using Thompson Sampling"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        total_budget = context.get("total_budget", self.settings.max_daily_spend_usd)

        # Step 1: Get active experiments with financials
        experiments = await self._get_experiment_financials()

        if not experiments:
            return AgentResult(success=True, data={"message": "No active experiments", "allocations": []})

        # Step 2: Score experiments by ROI
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
                description=f"Budget allocation: ROI score {alloc['roi_score']:.2f}",
                agent_name=self.name,
            ))

        # Step 5: Kill underperformers
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

        financials = []
        for exp in experiments:
            financials.append({
                "experiment_id": exp.id,
                "title": exp.title,
                "status": exp.status.value,
                "budget_spent": exp.budget_spent,
                "revenue_total": exp.revenue_total,
                "roi": (exp.revenue_total / exp.budget_spent - 1) if exp.budget_spent > 0 else 0.0,
            })
        return financials

    def _score_experiments(self, experiments: list[dict]) -> list[dict]:
        for exp in experiments:
            roi = exp["roi"]
            # Bayesian-inspired score: reward ROI, penalize high spend with no return
            if exp["budget_spent"] < 1.0:
                exp["roi_score"] = 0.5  # Exploration bonus for new experiments
            elif roi > 0:
                exp["roi_score"] = min(roi, 10.0) / 10.0  # Cap at 10x ROI
            else:
                exp["roi_score"] = max(roi, -1.0) / 10.0  # Negative but bounded
        return sorted(experiments, key=lambda e: e["roi_score"], reverse=True)

    def _allocate(self, scored: list[dict], total_budget: float) -> list[dict]:
        """Proportional allocation weighted by ROI score."""
        # Shift scores to positive
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
        """Kill experiments with ROI < -0.5 and spend > $5."""
        killed = []
        for exp in scored:
            if exp["roi"] < -0.5 and exp["budget_spent"] > 5.0:
                result = await self.db.execute(
                    select(Experiment).where(Experiment.id == exp["experiment_id"])
                )
                experiment = result.scalar_one_or_none()
                if experiment:
                    experiment.status = ExperimentStatus.killed
                    killed.append(exp["title"])
        return killed
