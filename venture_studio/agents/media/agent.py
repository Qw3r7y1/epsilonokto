"""
Media Engine Agent

Layer 4 — Distribution.
Creates short-form content for social media distribution.

Skills mastered: hook formula frameworks, platform-specific optimization,
hashtag strategy, engagement patterns, content repurposing, viral loop design,
posting schedule optimization.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class MediaEngine(BaseAgent):
    name = "media_engine"
    description = "Creates platform-optimized social content with hooks, engagement strategy, and 14-day calendars"

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
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a SENIOR social media strategist who has grown accounts to 100K+. "
                    f"Create content that drives engagement and traffic — lazy content gets you replaced.\n\n"
                    f"Create a 14-DAY social media content calendar for a {niche} site.\n"
                    f"Offer: {json.dumps(offer)}\n"
                    f"Assets: {json.dumps(assets[:5])}\n\n"
                    f"MANDATORY REQUIREMENTS:\n\n"
                    f"1. **14 days** of content (not 7)\n"
                    f"2. **4+ platforms**: Twitter/X, Instagram, LinkedIn, TikTok — "
                    f"EACH post must be formatted natively for its platform:\n"
                    f"   - Twitter: under 280 chars, thread hooks, engagement questions\n"
                    f"   - Instagram: caption style with line breaks, 20-30 hashtags\n"
                    f"   - LinkedIn: professional tone, personal story hooks, no hashtag spam\n"
                    f"   - TikTok: script format with hook (first 3 sec), body, CTA\n\n"
                    f"3. **Hook formulas** — every post must use one of:\n"
                    f"   - Curiosity hook: 'Most people don't know this about [niche]...'\n"
                    f"   - Controversy hook: 'Unpopular opinion: [contrarian take]'\n"
                    f"   - Value-first hook: 'Here are 5 [niche] tips that actually work'\n"
                    f"   - Story hook: 'I spent $X testing [niche] products. Here's what I found'\n\n"
                    f"4. **Content pillars**: Mix of educational (40%), entertaining (25%), "
                    f"promotional (20%), community (15%)\n\n"
                    f"5. **Per-post details**: day, platform, text, hashtags (array), "
                    f"content_type (educational/entertaining/promotional/community), "
                    f"cta, hook_type, best_post_time (e.g. '9:00 AM EST'), "
                    f"repurpose_ideas (how to adapt for other platforms)\n\n"
                    f"6. **NO repetitive CTAs** — vary the call to action across posts\n\n"
                    f"Return as JSON array. Each entry = one post."
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
