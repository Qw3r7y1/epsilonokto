"""
Venture Studio — Central Configuration

All settings are loaded from environment variables with sensible defaults.
"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings


class VentureSettings(BaseSettings):
    # ── App ──────────────────────────────────────────────────────────────
    app_name: str = "venture-studio"
    environment: Literal["dev", "staging", "prod"] = "dev"
    debug: bool = True
    api_prefix: str = "/api/vs/v1"

    # ── Database ─────────────────────────────────────────────────────────
    database_url: str = "postgresql+asyncpg://venture:venture@localhost:5433/venture"
    database_echo: bool = False

    # ── Redis / Celery ───────────────────────────────────────────────────
    redis_url: str = "redis://localhost:6380/0"
    celery_broker_url: str = "redis://localhost:6380/1"
    celery_result_backend: str = "redis://localhost:6380/2"

    # ── Claude API ───────────────────────────────────────────────────────
    anthropic_api_key: str = ""
    claude_model: str = "claude-sonnet-4-20250514"
    claude_max_tokens: int = 4096

    # ── SerpAPI ──────────────────────────────────────────────────────────
    serpapi_key: str = ""

    # ── Stripe ───────────────────────────────────────────────────────────
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""

    # ── Cloudflare R2 ────────────────────────────────────────────────────
    r2_account_id: str = ""
    r2_access_key: str = ""
    r2_secret_key: str = ""
    r2_bucket: str = "venture-assets"

    # ── Governance ───────────────────────────────────────────────────────
    global_kill_switch: bool = False
    max_daily_spend_usd: float = 50.0
    max_experiment_spend_usd: float = 20.0
    max_concurrent_experiments: int = 5
    circuit_breaker_threshold: int = 5  # consecutive failures before halt

    # ── Pods ─────────────────────────────────────────────────────────────
    active_pod: Literal["affiliate", "digital_product", "lead_gen", "micro_saas", "trend_media"] = "affiliate"

    # ── Observability ────────────────────────────────────────────────────
    log_level: str = "INFO"
    plausible_domain: str = ""
    metabase_url: str = ""

    model_config = {"env_prefix": "VS_", "env_file": ".env", "extra": "ignore"}


@lru_cache
def get_settings() -> VentureSettings:
    return VentureSettings()
