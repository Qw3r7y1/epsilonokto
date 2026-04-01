"""
Revenue Collector Agent

Layer 5/6 — Monetization & Finance.
Ingests revenue data from affiliate networks, Stripe, and ad platforms.
Records revenue in the budget ledger and updates experiment outcomes.

Skills mastered: revenue attribution, multi-source reconciliation,
anomaly detection, duplicate event detection, currency normalization.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, func as sqlfunc

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.core.logging import logger
from venture_studio.db.models import (
    BudgetLedger,
    Experiment,
    ExperimentStatus,
    LedgerEntryType,
    Outcome,
)


class RevenueCollector(BaseAgent):
    name = "revenue_collector"
    description = "Ingests revenue with duplicate detection, anomaly flagging, and accurate attribution"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        experiment_id = context.get("experiment_id")

        # Collect from all configured sources
        revenue_events: list[dict] = []

        stripe_events = await self._collect_stripe()
        revenue_events.extend(stripe_events)

        manual_events = context.get("revenue_events", [])
        revenue_events.extend(manual_events)

        # Record in ledger with duplicate detection
        total_revenue = 0.0
        duplicates_skipped = 0
        for event in revenue_events:
            amount = float(event.get("amount_usd", 0))
            description = event.get("description", "Revenue event")

            exp_id = event.get("experiment_id") or experiment_id
            if isinstance(exp_id, str):
                exp_id = uuid.UUID(exp_id)

            # Duplicate detection — check for same description + amount in last 24h
            is_duplicate = await self._is_duplicate_event(description, amount)
            if is_duplicate:
                duplicates_skipped += 1
                logger.info(f"RevenueCollector: skipping duplicate event: {description}")
                await self._audit("duplicate_revenue_skipped", details={
                    "description": description,
                    "amount_usd": amount,
                })
                continue

            total_revenue += amount

            self.db.add(BudgetLedger(
                experiment_id=exp_id,
                entry_type=LedgerEntryType.revenue,
                amount_usd=amount,
                category=event.get("source", "unknown"),
                description=description,
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

        # Anomaly detection — flag revenue spikes
        anomaly_detected = False
        spike_ratio = 0.0
        if experiment_id and total_revenue > 0:
            anomaly_detected, spike_ratio = await self._check_revenue_anomaly(
                experiment_id, total_revenue
            )

        # Record daily outcome snapshot if experiment specified
        if experiment_id:
            exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
            self.db.add(Outcome(
                experiment_id=exp_uuid,
                day=datetime.now(timezone.utc),
                revenue_usd=total_revenue,
                metrics={
                    "sources": [e.get("source") for e in revenue_events],
                    "duplicates_skipped": duplicates_skipped,
                    "anomaly_detected": anomaly_detected,
                    "spike_ratio": spike_ratio,
                },
            ))

        return AgentResult(
            success=True,
            data={
                "total_revenue": total_revenue,
                "events_processed": len(revenue_events) - duplicates_skipped,
                "duplicates_skipped": duplicates_skipped,
                "anomaly_detected": anomaly_detected,
                "spike_ratio": round(spike_ratio, 2),
            },
        )

    async def _is_duplicate_event(self, description: str, amount: float) -> bool:
        """Check if an identical event was already recorded in the last 24 hours."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        result = await self.db.execute(
            select(sqlfunc.count(BudgetLedger.id)).where(
                BudgetLedger.description == description,
                BudgetLedger.amount_usd == amount,
                BudgetLedger.entry_type == LedgerEntryType.revenue,
                BudgetLedger.created_at >= cutoff,
            )
        )
        count = result.scalar_one()
        return count > 0

    async def _check_revenue_anomaly(
        self, experiment_id: str | uuid.UUID, today_revenue: float
    ) -> tuple[bool, float]:
        """Detect revenue anomalies — flag if today's revenue > 3x 7-day average."""
        exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
        week_ago = datetime.now(timezone.utc) - timedelta(days=7)

        result = await self.db.execute(
            select(sqlfunc.coalesce(sqlfunc.avg(Outcome.revenue_usd), 0.0)).where(
                Outcome.experiment_id == exp_uuid,
                Outcome.day >= week_ago,
            )
        )
        avg_daily = result.scalar_one()

        if avg_daily > 0 and today_revenue > 3 * avg_daily:
            spike_ratio = today_revenue / avg_daily
            logger.warning(
                f"RevenueCollector: ANOMALY DETECTED for experiment {experiment_id} — "
                f"today ${today_revenue:.2f} is {spike_ratio:.1f}x the 7-day avg ${avg_daily:.2f}"
            )
            await self._audit("revenue_anomaly_detected", str(experiment_id), {
                "today_revenue": today_revenue,
                "avg_daily": avg_daily,
                "spike_ratio": spike_ratio,
            })
            return True, spike_ratio

        return False, 0.0

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
