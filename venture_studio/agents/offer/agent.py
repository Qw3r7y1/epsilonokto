"""
Offer Architect Agent

Layer 3 — Factory.
Designs the monetization offer (affiliate links, product bundles, lead magnets)
based on opportunity data and competitor analysis.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class OfferArchitect(BaseAgent):
    name = "offer_architect"
    description = "Designs monetization offers based on opportunity and competitor data"

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
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a monetization strategist for a {pod} venture.\n\n"
                    f"Niche: {niche}\n"
                    f"Opportunity data: {json.dumps(opportunity)}\n"
                    f"Competitor analysis: {json.dumps(competitor_analysis)}\n\n"
                    f"Design a complete monetization offer. Include:\n"
                    f"- offer_title: compelling name\n"
                    f"- offer_type: affiliate/digital_product/lead_magnet/tool\n"
                    f"- value_proposition: 1 sentence\n"
                    f"- target_audience: who this serves\n"
                    f"- monetization_method: how it makes money\n"
                    f"- affiliate_programs: list of relevant programs if applicable\n"
                    f"- content_plan: list of pages/articles to create\n"
                    f"- cta: primary call-to-action\n"
                    f"- estimated_conversion_rate: realistic estimate\n\n"
                    f"Return as JSON object."
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
            "content_plan": [f"best-{niche.replace(' ', '-')}", f"{niche.replace(' ', '-')}-guide"],
            "cta": "Check latest prices",
        }
