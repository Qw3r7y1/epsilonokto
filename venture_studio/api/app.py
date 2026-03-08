"""
Venture Studio — FastAPI Application
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from venture_studio.api.routes import agents, experiments, governance, orchestrator
from venture_studio.core.config import get_settings
from venture_studio.core.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    logger.info(f"Venture Studio starting — env={settings.environment}, pod={settings.active_pod}")
    yield
    logger.info("Venture Studio shutting down")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="Autonomous Venture Studio",
        version="0.1.0",
        lifespan=lifespan,
        docs_url=f"{settings.api_prefix}/docs",
        openapi_url=f"{settings.api_prefix}/openapi.json",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.debug else [],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Mount routes
    app.include_router(experiments.router, prefix=settings.api_prefix)
    app.include_router(agents.router, prefix=settings.api_prefix)
    app.include_router(governance.router, prefix=settings.api_prefix)
    app.include_router(orchestrator.router, prefix=settings.api_prefix)

    @app.get("/health")
    async def health():
        return {
            "status": "ok",
            "service": "venture-studio",
            "kill_switch": settings.global_kill_switch,
            "active_pod": settings.active_pod,
        }

    return app


app = create_app()
