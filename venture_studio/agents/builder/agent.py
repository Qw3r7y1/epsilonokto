"""
Builder Agent

Layer 3 — Factory.
Generates digital assets: landing pages, blog posts, tool pages, etc.
Uses Claude to generate content and stores assets in R2 / database.

Skills mastered: SEO content writing, E-E-A-T optimization, conversion
copywriting, structured data markup, internal linking, above-the-fold optimization.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.db.models import Asset, AssetType


class BuilderAgent(BaseAgent):
    name = "builder"
    description = "Builds expert-quality digital assets with E-E-A-T, schema markup, and conversion optimization"

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
            max_tokens=8192,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a SENIOR content strategist and SEO copywriter. "
                    f"Write content that ranks #1 and converts — anything less and you're replaced.\n\n"
                    f"Create a high-quality, SEO-optimized article for: {slug}\n"
                    f"Niche: {niche}\n"
                    f"Value proposition: {offer.get('value_proposition', '')}\n"
                    f"Target audience: {offer.get('target_audience', '')}\n"
                    f"CTA: {offer.get('cta', '')}\n\n"
                    f"MANDATORY REQUIREMENTS — every single one:\n\n"
                    f"1. **Length**: 2000+ words minimum. Comprehensive, no fluff.\n"
                    f"2. **E-E-A-T Signals**: Include author expertise signals, data citations "
                    f"with specific numbers/stats, and expert-level analysis\n"
                    f"3. **Above-the-fold**: First 200 words must hook reader AND include "
                    f"primary keyword AND deliver immediate value\n"
                    f"4. **Heading hierarchy**: Proper H2/H3/H4 structure. "
                    f"Every H2 targets a keyword variation\n"
                    f"5. **Table of Contents**: At the top of the article\n"
                    f"6. **Comparison tables**: Where relevant — product vs product with "
                    f"features, pricing, pros/cons columns\n"
                    f"7. **Pros/Cons sections**: For every reviewed item\n"
                    f"8. **FAQ Schema section**: At least 5 Q&A pairs formatted as:\n"
                    f"   ## Frequently Asked Questions\n"
                    f"   ### Q: [question]?\n"
                    f"   A: [detailed answer]\n"
                    f"9. **Internal linking placeholders**: Use [INTERNAL_LINK: related-slug] "
                    f"markers where related content should link\n"
                    f"10. **Natural CTA placements**: 3-4 CTAs woven naturally into content "
                    f"(not forced). First CTA within first 500 words\n"
                    f"11. **Meta description**: Under 160 chars, includes primary keyword and CTA\n"
                    f"12. **Mobile-friendly formatting**: Short paragraphs (2-3 sentences max), "
                    f"bullet lists, bold key phrases\n\n"
                    f"Return JSON with keys: title, slug, body (markdown), meta_description, "
                    f"headings (list), faq_schema (list of {{question, answer}}), "
                    f"internal_links (list of suggested slugs), word_count (int)."
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
