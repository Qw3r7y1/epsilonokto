"""
Offer Architect Agent

Layer 3 — Factory.
Designs the monetization offer (affiliate links, product bundles, lead magnets)
based on opportunity data and competitor analysis.

Skills mastered: conversion funnel design, pricing psychology, value ladder
construction, A/B test planning, USP formulation, audience segmentation.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class OfferArchitect(BaseAgent):
    name = "offer_architect"
    description = "Designs expert-level monetization offers with full funnel strategy"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        niche = context.get("niche", "")
        pod = context.get("pod", self.settings.active_pod)
        competitor_analysis = context.get("competitor_analysis", {})
        opportunity = context.get("opportunity", {})

        if not niche:
            return AgentResult(success=False, error="No niche provided")

        offer, cost = await self._design_offer(niche, pod, competitor_analysis, opportunity)
        return AgentResult(success=True, data={"offer": offer}, spend_usd=cost)

    async def _design_offer(
        self, niche: str, pod: str, competitor_analysis: dict, opportunity: dict
    ) -> tuple[dict, float]:
        if not self.settings.anthropic_api_key:
            return self._default_offer(niche, pod), 0.0

        import anthropic
        import json

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)

        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a SENIOR monetization strategist for a {pod} venture. "
                    f"Design a complete, conversion-optimized offer. Mediocre work gets you replaced.\n\n"
                    f"Niche: {niche}\n"
                    f"Opportunity data: {json.dumps(opportunity)}\n"
                    f"Competitor analysis: {json.dumps(competitor_analysis)}\n\n"
                    f"Design a COMPLETE monetization offer with ALL of the following:\n\n"
                    f"- offer_title: compelling, benefit-driven name\n"
                    f"- offer_type: affiliate | digital_product | lead_magnet | tool\n"
                    f"- value_proposition: 1 sentence that makes the audience stop scrolling\n"
                    f"- target_audience: specific persona (age, interests, pain points)\n"
                    f"- audience_segments: at least 3 micro-segments with tailored messaging\n"
                    f"- monetization_method: primary revenue stream with specifics\n"
                    f"- affiliate_programs: list of specific programs with commission rates if applicable\n"
                    f"- value_ladder: object with tiers — free (lead magnet), low_ticket ($1-$50), "
                    f"mid_ticket ($50-$500), high_ticket ($500+)\n"
                    f"- funnel_stages: awareness → consideration → decision → retention with tactics per stage\n"
                    f"- content_plan: list of 5+ specific pages/articles to create with target keywords\n"
                    f"- lead_magnet: specific freebie to capture emails (checklist, template, guide)\n"
                    f"- cta: primary call-to-action with urgency element\n"
                    f"- pricing_psychology: anchoring, decoy, or bundle strategy\n"
                    f"- ab_test_plan: 2-3 variations to test for the main offer\n"
                    f"- upsell_strategy: cross-sell or upsell path after initial conversion\n"
                    f"- estimated_conversion_rate: realistic estimate with reasoning\n"
                    f"- revenue_projections: month_1, month_3, month_6 estimates with assumptions\n\n"
                    f"Return as JSON object. Every field is REQUIRED."
                ),
            }],
        )

        try:
            text = message.content[0].text
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            offer = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            offer = self._default_offer(niche, pod)

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return offer, cost

    def _default_offer(self, niche: str, pod: str) -> dict:
        return {
            "offer_title": f"Best {niche.title()} Guide",
            "offer_type": "affiliate",
            "value_proposition": f"Comprehensive guide to the best {niche} products",
            "target_audience": f"People searching for {niche} recommendations",
            "monetization_method": "affiliate commissions",
            "content_plan": [
                f"best-{niche.replace(' ', '-')}",
                f"{niche.replace(' ', '-')}-guide",
                f"{niche.replace(' ', '-')}-reviews",
                f"{niche.replace(' ', '-')}-comparison",
                f"how-to-choose-{niche.replace(' ', '-')}",
            ],
            "cta": "Check latest prices",
            "lead_magnet": f"Free {niche.title()} Buyer's Checklist",
        }
