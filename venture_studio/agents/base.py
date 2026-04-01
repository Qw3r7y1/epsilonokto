"""
Base Agent Framework

Every agent in the venture studio inherits from BaseAgent.
This provides:
  - governance checks (kill switch, budget, circuit breaker)
  - performance accountability (tracking, warnings, replacement flags)
  - audit logging
  - structured input/output
  - error handling with automatic circuit breaker
  - budget tracking
"""

from __future__ import annotations

import abc
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, func as sqlfunc
from sqlalchemy.ext.asyncio import AsyncSession

from venture_studio.core.config import get_settings
from venture_studio.core.exceptions import (
    AgentDisabled,
    BudgetExceeded,
    CircuitBreakerOpen,
    KillSwitchActive,
)
from venture_studio.core.logging import logger
from venture_studio.db.models import (
    Agent as AgentModel,
    AgentStatus,
    AuditLog,
    BudgetLedger,
    LedgerEntryType,
)
from venture_studio.governance.policies import (
    get_performance_standard,
    get_required_skills,
)


class AgentResult:
    """Structured result from an agent run."""

    def __init__(
        self,
        success: bool,
        data: dict[str, Any] | None = None,
        error: str | None = None,
        spend_usd: float = 0.0,
    ):
        self.success = success
        self.data = data or {}
        self.error = error
        self.spend_usd = spend_usd


class BaseAgent(abc.ABC):
    """Abstract base for all venture studio agents."""

    name: str = "base_agent"
    description: str = "Base agent"

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    # ── Abstract ─────────────────────────────────────────────────────────

    @abc.abstractmethod
    async def execute(self, context: dict[str, Any]) -> AgentResult:
        """Agent-specific logic. Must return AgentResult."""
        ...

    # ── Public entry point ───────────────────────────────────────────────

    async def run(self, context: dict[str, Any] | None = None) -> AgentResult:
        """Run the agent with full governance wrapping."""
        context = context or {}
        agent_record = await self._get_or_create_record()

        try:
            # Pre-flight checks
            await self._check_kill_switch()
            await self._check_agent_enabled(agent_record)
            await self._check_circuit_breaker(agent_record)
            await self._check_daily_budget()

            # Mark running
            agent_record.status = AgentStatus.running
            agent_record.last_run_at = datetime.now(timezone.utc)
            agent_record.total_runs += 1
            await self.db.flush()

            await self._audit("run_start", context.get("experiment_id"), {"context_keys": list(context.keys())})

            # Execute
            result = await self.execute(context)

            # Record spend
            if result.spend_usd > 0:
                await self._record_spend(result.spend_usd, context.get("experiment_id"), "agent_run")

            # Update agent state
            if result.success:
                agent_record.status = AgentStatus.idle
                agent_record.consecutive_failures = 0
                agent_record.total_successes += 1
            else:
                agent_record.consecutive_failures += 1
                agent_record.total_failures += 1
                agent_record.status = AgentStatus.errored

            await self._audit(
                "run_complete" if result.success else "run_failed",
                context.get("experiment_id"),
                {"success": result.success, "error": result.error, "spend": result.spend_usd},
            )

            # Performance accountability — non-blocking
            try:
                await self._check_performance_standing(agent_record)
            except Exception:
                logger.debug(f"Agent {self.name}: performance check skipped (non-critical)")

            await self.db.commit()
            return result

        except (KillSwitchActive, BudgetExceeded, AgentDisabled, CircuitBreakerOpen) as gov_err:
            await self._audit("governance_block", context.get("experiment_id"), {"error": str(gov_err)})
            agent_record.status = AgentStatus.paused
            await self.db.commit()
            logger.warning(f"Agent {self.name} blocked: {gov_err}")
            return AgentResult(success=False, error=str(gov_err))

        except Exception as exc:
            agent_record.consecutive_failures += 1
            agent_record.total_failures += 1
            agent_record.status = AgentStatus.errored
            await self._audit("run_exception", context.get("experiment_id"), {"error": traceback.format_exc()})
            await self.db.commit()
            logger.error(f"Agent {self.name} exception: {exc}")
            return AgentResult(success=False, error=str(exc))

    # ── Governance checks ────────────────────────────────────────────────

    async def _check_kill_switch(self) -> None:
        if self.settings.global_kill_switch:
            raise KillSwitchActive("Global kill switch is active")

    async def _check_agent_enabled(self, record: AgentModel) -> None:
        if not record.enabled:
            raise AgentDisabled(f"Agent {self.name} is disabled")

    async def _check_circuit_breaker(self, record: AgentModel) -> None:
        if record.consecutive_failures >= self.settings.circuit_breaker_threshold:
            raise CircuitBreakerOpen(
                f"Agent {self.name} circuit breaker open "
                f"({record.consecutive_failures} consecutive failures)"
            )

    async def _check_daily_budget(self) -> None:
        today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        result = await self.db.execute(
            select(sqlfunc.coalesce(sqlfunc.sum(BudgetLedger.amount_usd), 0.0)).where(
                BudgetLedger.entry_type == LedgerEntryType.spend,
                BudgetLedger.created_at >= today_start,
            )
        )
        daily_spend = result.scalar_one()
        if daily_spend >= self.settings.max_daily_spend_usd:
            raise BudgetExceeded(
                f"Daily spend ${daily_spend:.2f} >= limit ${self.settings.max_daily_spend_usd:.2f}"
            )

    # ── Performance accountability ───────────────────────────────────────

    async def _check_performance_standing(self, record: AgentModel) -> None:
        """Evaluate agent performance against standards. Audit warnings/flags."""
        standard = get_performance_standard(self.name)
        min_runs = standard["min_runs_before_review"]

        if record.total_runs < min_runs:
            return  # Not enough data to evaluate

        success_rate = record.total_successes / record.total_runs if record.total_runs > 0 else 0.0
        max_failures = standard["max_consecutive_failures_before_replacement"]

        # Check success rate
        if success_rate < standard["min_success_rate"]:
            logger.warning(
                f"Agent {self.name} performance below threshold: "
                f"{success_rate:.1%} < {standard['min_success_rate']:.0%} "
                f"({record.total_runs} runs)"
            )
            await self._audit("performance_warning", details={
                "success_rate": round(success_rate, 3),
                "threshold": standard["min_success_rate"],
                "total_runs": record.total_runs,
                "total_successes": record.total_successes,
                "total_failures": record.total_failures,
                "required_skills": get_required_skills(self.name),
            })

        # Check replacement threshold
        if record.consecutive_failures >= max_failures:
            logger.error(
                f"Agent {self.name} FLAGGED FOR REPLACEMENT: "
                f"{record.consecutive_failures} consecutive failures "
                f"(threshold: {max_failures})"
            )
            await self._audit("replacement_flagged", details={
                "consecutive_failures": record.consecutive_failures,
                "replacement_threshold": max_failures,
                "success_rate": round(success_rate, 3),
                "agent_name": self.name,
            })

    def _get_performance_report(self, record: AgentModel) -> dict:
        """Return a performance summary for this agent."""
        standard = get_performance_standard(self.name)
        success_rate = record.total_successes / record.total_runs if record.total_runs > 0 else 0.0
        max_failures = standard["max_consecutive_failures_before_replacement"]

        if record.total_runs < standard["min_runs_before_review"]:
            standing = "probationary"
        elif record.consecutive_failures >= max_failures:
            standing = "replacement_flagged"
        elif success_rate < standard["min_success_rate"]:
            standing = "underperforming"
        else:
            standing = "good"

        return {
            "agent_name": self.name,
            "total_runs": record.total_runs,
            "total_successes": record.total_successes,
            "total_failures": record.total_failures,
            "success_rate": round(success_rate, 3),
            "consecutive_failures": record.consecutive_failures,
            "standing": standing,
            "min_success_rate": standard["min_success_rate"],
            "required_skills": get_required_skills(self.name),
        }

    # ── Helpers ──────────────────────────────────────────────────────────

    async def _get_or_create_record(self) -> AgentModel:
        result = await self.db.execute(
            select(AgentModel).where(AgentModel.name == self.name)
        )
        record = result.scalar_one_or_none()
        if not record:
            record = AgentModel(name=self.name, description=self.description)
            self.db.add(record)
            await self.db.flush()
        return record

    async def _audit(
        self, action: str, experiment_id: uuid.UUID | str | None = None, details: dict | None = None
    ) -> None:
        exp_id = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
        self.db.add(
            AuditLog(
                agent_name=self.name,
                action=action,
                experiment_id=exp_id,
                details=details,
            )
        )
        await self.db.flush()

    async def _record_spend(
        self, amount: float, experiment_id: uuid.UUID | str | None = None, category: str = "general"
    ) -> None:
        exp_id = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
        self.db.add(
            BudgetLedger(
                experiment_id=exp_id,
                entry_type=LedgerEntryType.spend,
                amount_usd=amount,
                category=category,
                description=f"{self.name} execution",
                agent_name=self.name,
            )
        )
        await self.db.flush()
