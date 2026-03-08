"""
Venture Studio Orchestrator

Manages the core system loop:
  discover → score → validate → build → publish → distribute → collect → analyze → allocate → learn

Coordinates agents in the correct sequence with proper data passing
and experiment lifecycle management.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from venture_studio.agents.registry import get_agent
from venture_studio.core.config import get_settings
from venture_studio.core.exceptions import KillSwitchActive
from venture_studio.core.logging import logger
from venture_studio.db.models import Experiment, ExperimentStatus


class Orchestrator:
    """Drives the experiment lifecycle through agent stages."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings = get_settings()

    # ── Full Cycle ───────────────────────────────────────────────────────

    async def run_discovery_cycle(self) -> dict[str, Any]:
        """Run a full discovery → scoring cycle. Creates new experiments."""
        self._check_kill_switch()

        # 1. Opportunity Scout
        scout_cls = get_agent("opportunity_scout")
        scout = scout_cls(self.db)
        result = await scout.run({"pod": self.settings.active_pod})

        if not result.success:
            return {"stage": "discovery", "error": result.error}

        opportunities = result.data.get("opportunities", [])
        created_experiments = []

        for opp in opportunities[:self.settings.max_concurrent_experiments]:
            exp = Experiment(
                title=opp.get("title", "Untitled"),
                niche=opp.get("niche", "unknown"),
                score=opp.get("score", 0.5),
                hypothesis=opp.get("hypothesis", ""),
                status=ExperimentStatus.discovered,
                metadata_=opp,
            )
            self.db.add(exp)
            await self.db.flush()
            created_experiments.append(str(exp.id))

        await self.db.commit()
        return {"stage": "discovery", "experiments_created": len(created_experiments), "ids": created_experiments}

    async def advance_experiment(self, experiment_id: str | uuid.UUID) -> dict[str, Any]:
        """Advance a single experiment to its next stage."""
        self._check_kill_switch()

        exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id
        result = await self.db.execute(
            select(Experiment).where(Experiment.id == exp_uuid)
        )
        exp = result.scalar_one_or_none()
        if not exp:
            return {"error": f"Experiment {experiment_id} not found"}

        stage_map = {
            ExperimentStatus.discovered: self._stage_score,
            ExperimentStatus.scoring: self._stage_validate,
            ExperimentStatus.validated: self._stage_build,
            ExperimentStatus.building: self._stage_publish,
            ExperimentStatus.published: self._stage_distribute,
            ExperimentStatus.distributing: self._stage_monitor,
            ExperimentStatus.monitoring: self._stage_analyze,
        }

        handler = stage_map.get(exp.status)
        if not handler:
            return {"experiment_id": str(exp.id), "status": exp.status.value, "message": "No further stages"}

        return await handler(exp)

    # ── Stage Handlers ───────────────────────────────────────────────────

    async def _stage_score(self, exp: Experiment) -> dict:
        """Score: run competitor analysis."""
        exp.status = ExperimentStatus.scoring

        mapper_cls = get_agent("competitor_mapper")
        mapper = mapper_cls(self.db)
        result = await mapper.run({"niche": exp.niche, "experiment_id": str(exp.id)})

        if result.success:
            exp.metadata_ = {**(exp.metadata_ or {}), "competitor_analysis": result.data}
        await self.db.commit()
        return {"stage": "scoring", "success": result.success, "experiment_id": str(exp.id)}

    async def _stage_validate(self, exp: Experiment) -> dict:
        """Validate: design the offer."""
        exp.status = ExperimentStatus.validated

        architect_cls = get_agent("offer_architect")
        architect = architect_cls(self.db)
        result = await architect.run({
            "niche": exp.niche,
            "pod": exp.pod.value,
            "competitor_analysis": (exp.metadata_ or {}).get("competitor_analysis", {}),
            "opportunity": exp.metadata_ or {},
            "experiment_id": str(exp.id),
        })

        if result.success:
            exp.metadata_ = {**(exp.metadata_ or {}), "offer": result.data.get("offer", {})}
        await self.db.commit()
        return {"stage": "validated", "success": result.success, "experiment_id": str(exp.id)}

    async def _stage_build(self, exp: Experiment) -> dict:
        """Build: create digital assets."""
        exp.status = ExperimentStatus.building

        builder_cls = get_agent("builder")
        builder = builder_cls(self.db)
        offer = (exp.metadata_ or {}).get("offer", {})
        result = await builder.run({
            "experiment_id": str(exp.id),
            "niche": exp.niche,
            "offer": offer,
        })

        if result.success:
            exp.metadata_ = {**(exp.metadata_ or {}), "built_assets": result.data.get("assets", [])}
        await self.db.commit()
        return {"stage": "building", "success": result.success, "experiment_id": str(exp.id)}

    async def _stage_publish(self, exp: Experiment) -> dict:
        """Publish: deploy assets."""
        publisher_cls = get_agent("publisher")
        publisher = publisher_cls(self.db)
        result = await publisher.run({"experiment_id": str(exp.id)})

        if result.success:
            exp.status = ExperimentStatus.published
        await self.db.commit()
        return {"stage": "published", "success": result.success, "experiment_id": str(exp.id)}

    async def _stage_distribute(self, exp: Experiment) -> dict:
        """Distribute: SEO + social media."""
        exp.status = ExperimentStatus.distributing

        # Run SEO and Media in sequence
        offer = (exp.metadata_ or {}).get("offer", {})
        seo_cls = get_agent("seo_operator")
        seo = seo_cls(self.db)
        seo_result = await seo.run({
            "niche": exp.niche,
            "content_plan": offer.get("content_plan", []),
            "experiment_id": str(exp.id),
        })

        media_cls = get_agent("media_engine")
        media = media_cls(self.db)
        media_result = await media.run({
            "niche": exp.niche,
            "offer": offer,
            "assets": (exp.metadata_ or {}).get("built_assets", []),
            "experiment_id": str(exp.id),
        })

        exp.metadata_ = {
            **(exp.metadata_ or {}),
            "seo_plan": seo_result.data if seo_result.success else {},
            "social_content": media_result.data if media_result.success else {},
        }
        await self.db.commit()
        return {
            "stage": "distributing",
            "seo_success": seo_result.success,
            "media_success": media_result.success,
            "experiment_id": str(exp.id),
        }

    async def _stage_monitor(self, exp: Experiment) -> dict:
        """Monitor: collect revenue data."""
        exp.status = ExperimentStatus.monitoring

        collector_cls = get_agent("revenue_collector")
        collector = collector_cls(self.db)
        result = await collector.run({"experiment_id": str(exp.id)})

        await self.db.commit()
        return {"stage": "monitoring", "success": result.success, "experiment_id": str(exp.id)}

    async def _stage_analyze(self, exp: Experiment) -> dict:
        """Analyze: capital allocation + strategy extraction."""
        allocator_cls = get_agent("capital_allocator")
        allocator = allocator_cls(self.db)
        alloc_result = await allocator.run({"experiment_id": str(exp.id)})

        # Mark as winning if profitable
        if exp.revenue_total > exp.budget_spent and exp.budget_spent > 0:
            exp.status = ExperimentStatus.winning

            # Extract strategy
            librarian_cls = get_agent("strategy_librarian")
            librarian = librarian_cls(self.db)
            await librarian.run({"experiment_id": str(exp.id)})

        await self.db.commit()
        return {"stage": "analyze", "success": alloc_result.success, "experiment_id": str(exp.id)}

    # ── Recursive improvement ────────────────────────────────────────────

    async def run_recursive_improvement(self) -> dict[str, Any]:
        """Run the Agent Architect to propose/create new agents."""
        self._check_kill_switch()

        architect_cls = get_agent("agent_architect")
        architect = architect_cls(self.db)

        # Phase 1: Analyze
        analysis = await architect.run({"mode": "analyze"})
        if not analysis.success:
            return {"stage": "recursive_improvement", "error": analysis.error}

        proposals = analysis.data.get("proposals", [])
        created = []

        # Phase 2: Create approved proposals
        for proposal in proposals:
            result = await architect.run({"mode": "create", "proposal": proposal})
            if result.success:
                created.append(result.data.get("agent_name"))

        # Phase 3: Cleanup failed experimental agents
        cleanup = await architect.run({"mode": "cleanup"})

        await self.db.commit()
        return {
            "stage": "recursive_improvement",
            "proposals": len(proposals),
            "created": created,
            "cleanup": cleanup.data if cleanup.success else {},
        }

    # ── Governance run ───────────────────────────────────────────────────

    async def run_governance_check(self) -> dict[str, Any]:
        """Run governance controller for system health audit."""
        gov_cls = get_agent("governance_controller")
        gov = gov_cls(self.db)
        result = await gov.run({})
        await self.db.commit()
        return result.data if result.success else {"error": result.error}

    # ── Helpers ──────────────────────────────────────────────────────────

    def _check_kill_switch(self) -> None:
        if self.settings.global_kill_switch:
            raise KillSwitchActive("Global kill switch is active")
