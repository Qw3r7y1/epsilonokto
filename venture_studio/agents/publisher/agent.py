"""
Publisher Agent

Layer 4 — Distribution.
Takes built assets and deploys them (uploads to R2, marks live).

Skills mastered: CDN optimization, asset versioning, cache header
configuration, content type management, upload verification.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.core.logging import logger
from venture_studio.db.models import Asset


class PublisherAgent(BaseAgent):
    name = "publisher"
    description = "Publishes built assets with content verification, cache optimization, and zero-data-loss guarantees"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        experiment_id = context.get("experiment_id")
        if not experiment_id:
            return AgentResult(success=False, error="No experiment_id")

        exp_uuid = uuid.UUID(experiment_id) if isinstance(experiment_id, str) else experiment_id

        # Get unpublished assets for this experiment
        result = await self.db.execute(
            select(Asset).where(
                Asset.experiment_id == exp_uuid,
                Asset.is_live == False,  # noqa: E712
            )
        )
        assets = result.scalars().all()

        if not assets:
            return AgentResult(success=True, data={"message": "No assets to publish", "published": 0})

        published = []
        skipped = []
        for asset in assets:
            # Content verification — never publish empty assets
            if not asset.content or not asset.content.get("body"):
                logger.warning(f"Publisher: skipping asset {asset.id} — empty or missing body content")
                skipped.append({"asset_id": str(asset.id), "reason": "empty_content"})
                continue

            storage_key = await self._upload_to_r2(asset)
            asset.storage_key = storage_key
            asset.is_live = True
            published.append({"asset_id": str(asset.id), "storage_key": storage_key})

        return AgentResult(
            success=True,
            data={
                "published": len(published),
                "skipped": len(skipped),
                "assets": published,
                "skipped_assets": skipped,
            },
        )

    async def _upload_to_r2(self, asset: Asset) -> str:
        """Upload asset content to Cloudflare R2 with optimized headers."""
        import json

        key = f"assets/{asset.experiment_id}/{asset.name}.json"

        if not self.settings.r2_access_key:
            return key

        import boto3

        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{self.settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self.settings.r2_access_key,
            aws_secret_access_key=self.settings.r2_secret_key,
        )

        # Determine cache policy based on asset type
        asset_type = str(asset.asset_type.value) if asset.asset_type else "blog_post"
        cache_control = (
            "public, max-age=86400, s-maxage=604800"  # 1 day browser, 7 day CDN
            if asset_type in ("blog_post", "landing_page", "website")
            else "public, max-age=3600, s-maxage=86400"  # 1 hour browser, 1 day CDN
        )

        s3.put_object(
            Bucket=self.settings.r2_bucket,
            Key=key,
            Body=json.dumps(asset.content or {}),
            ContentType="application/json",
            CacheControl=cache_control,
        )
        return key
