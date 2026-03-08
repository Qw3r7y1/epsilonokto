"""
Media Engine Agent

Layer 4 — Distribution.
Creates short-form content for social media distribution.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class MediaEngine(BaseAgent):
    name = "media_engine"
    description = "Creates social media content and distribution plans"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        niche = context.get("niche", "")
        offer = context.get("offer", {})
        assets = context.get("assets", [])

        if not niche:
            return AgentResult(success=False, error="No niche provided")

        content, cost = await self._generate_social_content(niche, offer, assets)

        return AgentResult(
            success=True,
            data={"social_content": content},
            spend_usd=cost,
        )

    async def _generate_social_content(
        self, niche: str, offer: dict, assets: list[dict]
    ) -> tuple[list[dict], float]:
        if not self.settings.anthropic_api_key:
            return [{"platform": "twitter", "text": f"Check out our {niche} guide!", "type": "promotional"}], 0.0

        import anthropic
        import json

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    f"Create a 7-day social media content calendar for a {niche} site.\n"
                    f"Offer: {json.dumps(offer)}\n"
                    f"Assets: {json.dumps(assets[:5])}\n\n"
                    f"For each day, provide: platform, text, hashtags, content_type, cta.\n"
                    f"Focus on value-first content with subtle CTAs.\n"
                    f"Return as JSON array."
                ),
            }],
        )

        try:
            text = message.content[0].text
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            content = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            content = [{"platform": "generic", "text": message.content[0].text}]

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return content, cost
