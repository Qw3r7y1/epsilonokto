"""
Revenue Collector Agent

Layer 5/6 — Monetization & Finance.
Ingests revenue data from affiliate networks, Stripe, and ad platforms.
Records revenue in the budget ledger and updates experiment outcomes.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.db.models import (
    BudgetLedger,
    Experiment,
    ExperimentStatus,
    LedgerEntryType,
    Outcome,
)


class RevenueCollector(BaseAgent):
    name = "revenue_collector"
    description = "Ingests revenue data from external sources and updates experiment financials"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        experiment_id = context.get("experiment_id")

        # Collect from all configured sources
        revenue_events: list[dict] = []

        stripe_events = await self._collect_stripe()
        revenue_events.extend(stripe_events)

        # Future: affiliate network APIs, ad revenue, etc.
        manual_events = context.get("revenue_events", [])
        revenue_events.extend(manual_events)

        # Record in ledger
        total_revenue = 0.0
        for event in revenue_events:
            amount = float(event.get("amount_usd", 0))
            total_revenue += amount

            exp_id = event.get("experiment_id") or experiment_id
            if isinstance(exp_id, str):
                exp_id = uuid.UUID(exp_id)

            self.db.add(BudgetLedger(
                experiment_id=exp_id,
                entry_type=LedgerEntryType.revenue,
                amount_usd=amount,
                category=event.get("source", "unknown"),
                description=event.get("description", "Revenue event"),
                agent_name=self.name,
            ))

            # Update experiment revenue total
            if exp_id:
                result = await self.db.execute(
                    select(Experiment).where(Experiment.id == exp_id)
                )
                exp = result.scalar_one_or_none()
                if exp:
                    exp.revenue_total += amount

        # Record daily outcome snapshot if experiment specified
        if experiment_id:
            exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
            self.db.add(Outcome(
                experiment_id=exp_uuid,
                day=datetime.now(timezone.utc),
                revenue_usd=total_revenue,
                metrics={"sources": [e.get("source") for e in revenue_events]},
            ))

        return AgentResult(
            success=True,
            data={"total_revenue": total_revenue, "events_processed": len(revenue_events)},
        )

    async def _collect_stripe(self) -> list[dict]:
        """Pull recent charges from Stripe."""
        if not self.settings.stripe_secret_key:
            return []

        import stripe

        stripe.api_key = self.settings.stripe_secret_key
        charges = stripe.Charge.list(limit=50, created={"gte": int((datetime.now(timezone.utc).timestamp()) - 86400)})

        events = []
        for charge in charges.data:
            if charge.status == "succeeded":
                events.append({
                    "amount_usd": charge.amount / 100,
                    "source": "stripe",
                    "description": f"Stripe charge {charge.id}",
                    "experiment_id": charge.metadata.get("experiment_id"),
                })
        return events
