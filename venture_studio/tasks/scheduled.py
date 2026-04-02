"""
Scheduled Celery tasks for the Venture Studio.

These tasks bridge the async orchestrator with Celery's sync workers
by running the async code in an event loop.
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from venture_studio.core.logging import logger
from venture_studio.db.models import Experiment, ExperimentStatus
from venture_studio.db.session import async_session_factory
from venture_studio.services.orchestrator import Orchestrator
from venture_studio.tasks.celery_app import celery_app


def _run_async(coro):
    """Run an async coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="venture_studio.tasks.scheduled.discovery_cycle")
def discovery_cycle():
    async def _run():
        async with async_session_factory() as db:
            orch = Orchestrator(db)
            result = await orch.run_discovery_cycle()
            logger.info(f"Discovery cycle: {result}")
            return result
    return _run_async(_run())


@celery_app.task(name="venture_studio.tasks.scheduled.governance_check")
def governance_check():
    async def _run():
        async with async_session_factory() as db:
            orch = Orchestrator(db)
            result = await orch.run_governance_check()
            logger.info(f"Governance check: {result}")
            return result
    return _run_async(_run())


@celery_app.task(name="venture_studio.tasks.scheduled.revenue_collection")
def revenue_collection():
    async def _run():
        from venture_studio.agents.registry import get_agent
        async with async_session_factory() as db:
            collector_cls = get_agent("revenue_collector")
            collector = collector_cls(db)
            result = await collector.run({})
            await db.commit()
            logger.info(f"Revenue collection: {result.data}")
            return result.data
    return _run_async(_run())


@celery_app.task(name="venture_studio.tasks.scheduled.capital_allocation")
def capital_allocation():
    async def _run():
        from venture_studio.agents.registry import get_agent
        async with async_session_factory() as db:
            allocator_cls = get_agent("capital_allocator")
            allocator = allocator_cls(db)
            result = await allocator.run({})
            await db.commit()
            logger.info(f"Capital allocation: {result.data}")
            return result.data
    return _run_async(_run())


@celery_app.task(name="venture_studio.tasks.scheduled.strategy_extraction")
def strategy_extraction():
    async def _run():
        from venture_studio.agents.registry import get_agent
        async with async_session_factory() as db:
            librarian_cls = get_agent("strategy_librarian")
            librarian = librarian_cls(db)
            result = await librarian.run({})
            await db.commit()
            logger.info(f"Strategy extraction: {result.data}")
            return result.data
    return _run_async(_run())


@celery_app.task(name="venture_studio.tasks.scheduled.recursive_improvement")
def recursive_improvement():
    async def _run():
        async with async_session_factory() as db:
            orch = Orchestrator(db)
            result = await orch.run_recursive_improvement()
            logger.info(f"Recursive improvement: {result}")
            return result
    return _run_async(_run())


@celery_app.task(name="venture_studio.tasks.scheduled.advance_all_experiments")
def advance_all_experiments():
    """Advance all active experiments to their next stage."""
    async def _run():
        async with async_session_factory() as db:
            advanceable = [
                ExperimentStatus.discovered,
                ExperimentStatus.scoring,
                ExperimentStatus.validated,
                ExperimentStatus.building,
                ExperimentStatus.published,
                ExperimentStatus.distributing,
                ExperimentStatus.monitoring,
            ]
            result = await db.execute(
                select(Experiment).where(Experiment.status.in_(advanceable))
            )
            experiments = result.scalars().all()

            results = []
            orch = Orchestrator(db)
            for exp in experiments:
                try:
                    r = await orch.advance_experiment(exp.id)
                    results.append(r)
                except Exception as e:
                    logger.error(f"Failed to advance {exp.id}: {e}")
                    results.append({"experiment_id": str(exp.id), "error": str(e)})

            logger.info(f"Advanced {len(results)} experiments")
            return results
    return _run_async(_run())
