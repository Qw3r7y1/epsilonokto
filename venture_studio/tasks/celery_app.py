"""
Celery application configuration.
"""

from celery import Celery

from venture_studio.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "venture_studio",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    # Beat schedule
    beat_schedule={
        "discovery-cycle": {
            "task": "venture_studio.tasks.scheduled.discovery_cycle",
            "schedule": 3600.0,  # hourly
        },
        "governance-check": {
            "task": "venture_studio.tasks.scheduled.governance_check",
            "schedule": 900.0,  # every 15 minutes
        },
        "revenue-collection": {
            "task": "venture_studio.tasks.scheduled.revenue_collection",
            "schedule": 1800.0,  # every 30 minutes
        },
        "capital-allocation": {
            "task": "venture_studio.tasks.scheduled.capital_allocation",
            "schedule": 86400.0,  # daily
        },
        "strategy-extraction": {
            "task": "venture_studio.tasks.scheduled.strategy_extraction",
            "schedule": 86400.0,  # daily
        },
        "recursive-improvement": {
            "task": "venture_studio.tasks.scheduled.recursive_improvement",
            "schedule": 86400.0,  # daily
        },
        "advance-experiments": {
            "task": "venture_studio.tasks.scheduled.advance_all_experiments",
            "schedule": 3600.0,  # hourly
        },
    },
)

celery_app.autodiscover_tasks(["venture_studio.tasks"])
