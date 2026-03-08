"""
Builder Agent

Layer 3 — Factory.
Generates digital assets: landing pages, blog posts, tool pages, etc.
Uses Claude to generate content and stores assets in R2 / database.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.db.models import Asset, AssetType


class BuilderAgent(BaseAgent):
    name = "builder"
    description = "Builds digital assets (pages, posts, tools) from offer specifications"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        experiment_id = context.get("experiment_id")
        offer = context.get("offer", {})
        niche = context.get("niche", "")
        content_plan = offer.get("content_plan", [])

        if not experiment_id or not content_plan:
            return AgentResult(success=False, error="Missing experiment_id or content_plan")

        built_assets: list[dict] = []
        total_cost = 0.0

        for page_slug in content_plan:
            asset_data, cost = await self._build_page(niche, page_slug, offer)
            total_cost += cost

            # Persist asset
            asset = Asset(
                experiment_id=experiment_id,
                asset_type=AssetType.blog_post,
                name=page_slug,
                content=asset_data,
                is_live=False,
            )
            self.db.add(asset)
            await self.db.flush()

            built_assets.append({
                "asset_id": str(asset.id),
                "slug": page_slug,
                "title": asset_data.get("title", page_slug),
                "word_count": len(asset_data.get("body", "").split()),
            })

        return AgentResult(
            success=True,
            data={"assets": built_assets, "total_built": len(built_assets)},
            spend_usd=total_cost,
        )

    async def _build_page(self, niche: str, slug: str, offer: dict) -> tuple[dict, float]:
        if not self.settings.anthropic_api_key:
            return {
                "title": slug.replace("-", " ").title(),
                "slug": slug,
                "body": f"Placeholder content for {slug}",
                "meta_description": f"Guide about {niche}",
            }, 0.0

        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)

        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    f"Write a high-quality, SEO-optimized article for the page: {slug}\n"
                    f"Niche: {niche}\n"
                    f"Value proposition: {offer.get('value_proposition', '')}\n"
                    f"Target audience: {offer.get('target_audience', '')}\n"
                    f"CTA: {offer.get('cta', '')}\n\n"
                    f"Requirements:\n"
                    f"- 1500+ words\n"
                    f"- Use proper H2/H3 headings\n"
                    f"- Include practical advice\n"
                    f"- Natural affiliate CTA placements\n"
                    f"- Meta description (under 160 chars)\n\n"
                    f"Return JSON with keys: title, slug, body (markdown), meta_description, headings (list)."
                ),
            }],
        )

        import json
        try:
            text = message.content[0].text
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            page = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            page = {
                "title": slug.replace("-", " ").title(),
                "slug": slug,
                "body": message.content[0].text,
                "meta_description": f"Guide about {niche}",
            }

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return page, cost
