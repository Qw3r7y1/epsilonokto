"""Venture Studio initial schema

Revision ID: vs_0001
Revises:
Create Date: 2026-03-08
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision: str = "vs_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── vs_experiments ────────────────────────────────────────────────
    op.create_table(
        "vs_experiments",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("niche", sa.String(256), nullable=False),
        sa.Column("pod", sa.Enum("affiliate", "digital_product", "lead_gen", "micro_saas", "trend_media", name="podtype"), nullable=False, server_default="affiliate"),
        sa.Column("status", sa.Enum("discovered", "scoring", "validated", "building", "published", "distributing", "monitoring", "winning", "killed", "archived", name="experimentstatus"), nullable=False, server_default="discovered"),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("hypothesis", sa.Text, nullable=True),
        sa.Column("metadata", JSONB, nullable=True),
        sa.Column("budget_allocated", sa.Float, nullable=False, server_default="0"),
        sa.Column("budget_spent", sa.Float, nullable=False, server_default="0"),
        sa.Column("revenue_total", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vs_exp_status", "vs_experiments", ["status"])
    op.create_index("ix_vs_exp_pod", "vs_experiments", ["pod"])

    # ── vs_assets ─────────────────────────────────────────────────────
    op.create_table(
        "vs_assets",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("experiment_id", UUID(as_uuid=True), sa.ForeignKey("vs_experiments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_type", sa.Enum("website", "landing_page", "blog_post", "tool", "email_sequence", "video", "social_post", "product", name="assettype"), nullable=False),
        sa.Column("name", sa.String(512), nullable=False),
        sa.Column("url", sa.String(2048), nullable=True),
        sa.Column("storage_key", sa.String(1024), nullable=True),
        sa.Column("content", JSONB, nullable=True),
        sa.Column("is_live", sa.Boolean, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vs_asset_exp", "vs_assets", ["experiment_id"])

    # ── vs_agents ─────────────────────────────────────────────────────
    op.create_table(
        "vs_agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(128), unique=True, nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("status", sa.Enum("idle", "running", "paused", "errored", "disabled", name="agentstatus"), server_default="idle"),
        sa.Column("enabled", sa.Boolean, server_default="true"),
        sa.Column("consecutive_failures", sa.Integer, server_default="0"),
        sa.Column("total_runs", sa.Integer, server_default="0"),
        sa.Column("total_successes", sa.Integer, server_default="0"),
        sa.Column("total_failures", sa.Integer, server_default="0"),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("config", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── vs_budget_ledger ──────────────────────────────────────────────
    op.create_table(
        "vs_budget_ledger",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("experiment_id", UUID(as_uuid=True), sa.ForeignKey("vs_experiments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("entry_type", sa.Enum("spend", "revenue", "refund", "allocation", name="ledgerentrytype"), nullable=False),
        sa.Column("amount_usd", sa.Float, nullable=False),
        sa.Column("category", sa.String(128), nullable=False),
        sa.Column("description", sa.Text, server_default=""),
        sa.Column("agent_name", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vs_ledger_exp", "vs_budget_ledger", ["experiment_id"])
    op.create_index("ix_vs_ledger_type", "vs_budget_ledger", ["entry_type"])
    op.create_index("ix_vs_ledger_created", "vs_budget_ledger", ["created_at"])

    # ── vs_audit_log ──────────────────────────────────────────────────
    op.create_table(
        "vs_audit_log",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_name", sa.String(128), nullable=False),
        sa.Column("action", sa.String(256), nullable=False),
        sa.Column("experiment_id", UUID(as_uuid=True), sa.ForeignKey("vs_experiments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("details", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vs_audit_agent", "vs_audit_log", ["agent_name"])
    op.create_index("ix_vs_audit_created", "vs_audit_log", ["created_at"])

    # ── vs_outcomes ───────────────────────────────────────────────────
    op.create_table(
        "vs_outcomes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("experiment_id", UUID(as_uuid=True), sa.ForeignKey("vs_experiments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("day", sa.DateTime(timezone=True), nullable=False),
        sa.Column("impressions", sa.Integer, server_default="0"),
        sa.Column("clicks", sa.Integer, server_default="0"),
        sa.Column("conversions", sa.Integer, server_default="0"),
        sa.Column("revenue_usd", sa.Float, server_default="0"),
        sa.Column("spend_usd", sa.Float, server_default="0"),
        sa.Column("metrics", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vs_outcome_exp_day", "vs_outcomes", ["experiment_id", "day"])

    # ── vs_strategies ─────────────────────────────────────────────────
    op.create_table(
        "vs_strategies",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("experiment_id", UUID(as_uuid=True), sa.ForeignKey("vs_experiments.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(512), nullable=False),
        sa.Column("pod", sa.Enum("affiliate", "digital_product", "lead_gen", "micro_saas", "trend_media", name="podtype", create_type=False), nullable=False),
        sa.Column("niche", sa.String(256), nullable=False),
        sa.Column("playbook", JSONB, nullable=False),
        sa.Column("roi", sa.Float, nullable=True),
        sa.Column("reuse_count", sa.Integer, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_vs_strategy_pod", "vs_strategies", ["pod"])
    op.create_index("ix_vs_strategy_roi", "vs_strategies", ["roi"])


def downgrade() -> None:
    op.drop_table("vs_strategies")
    op.drop_table("vs_outcomes")
    op.drop_table("vs_audit_log")
    op.drop_table("vs_budget_ledger")
    op.drop_table("vs_agents")
    op.drop_table("vs_assets")
    op.drop_table("vs_experiments")

    # Drop enums
    for enum_name in ["podtype", "experimentstatus", "assettype", "agentstatus", "ledgerentrytype"]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
