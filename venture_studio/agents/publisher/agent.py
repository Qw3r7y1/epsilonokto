"""
Publisher Agent

Layer 4 — Distribution.
Takes built assets and deploys them (uploads to R2, marks live).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.db.models import Asset


class PublisherAgent(BaseAgent):
    name = "publisher"
    description = "Publishes built assets to hosting infrastructure"

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
        for asset in assets:
            storage_key = await self._upload_to_r2(asset)
            asset.storage_key = storage_key
            asset.is_live = True
            published.append({"asset_id": str(asset.id), "storage_key": storage_key})

        return AgentResult(
            success=True,
            data={"published": len(published), "assets": published},
        )

    async def _upload_to_r2(self, asset: Asset) -> str:
        """Upload asset content to Cloudflare R2. Returns storage key."""
        import json

        key = f"assets/{asset.experiment_id}/{asset.name}.json"

        if not self.settings.r2_access_key:
            # Stub: skip actual upload
            return key

        import boto3

        s3 = boto3.client(
            "s3",
            endpoint_url=f"https://{self.settings.r2_account_id}.r2.cloudflarestorage.com",
            aws_access_key_id=self.settings.r2_access_key,
            aws_secret_access_key=self.settings.r2_secret_key,
        )
        s3.put_object(
            Bucket=self.settings.r2_bucket,
            Key=key,
            Body=json.dumps(asset.content or {}),
            ContentType="application/json",
        )
        return key
