"""
SEO Operator Agent

Layer 4 — Distribution.
Handles keyword research, on-page SEO optimization, and indexing.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class SEOOperator(BaseAgent):
    name = "seo_operator"
    description = "Performs keyword research and SEO optimization for assets"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        niche = context.get("niche", "")
        content_plan = context.get("content_plan", [])

        if not niche:
            return AgentResult(success=False, error="No niche provided")

        # Step 1: Keyword research
        keywords, search_cost = await self._keyword_research(niche)

        # Step 2: Generate SEO recommendations
        recommendations, llm_cost = await self._generate_seo_plan(niche, keywords, content_plan)

        return AgentResult(
            success=True,
            data={
                "keywords": keywords,
                "recommendations": recommendations,
            },
            spend_usd=search_cost + llm_cost,
        )

    async def _keyword_research(self, niche: str) -> tuple[list[dict], float]:
        if not self.settings.serpapi_key:
            return [{"keyword": niche, "volume": "unknown", "difficulty": "unknown"}], 0.0

        import httpx

        keywords = []
        async with httpx.AsyncClient() as client:
            for q in [f"best {niche}", f"{niche} reviews", f"{niche} guide"]:
                resp = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": q,
                        "api_key": self.settings.serpapi_key,
                        "engine": "google",
                        "num": 10,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()
                related = data.get("related_searches", [])
                for r in related:
                    keywords.append({"keyword": r.get("query", ""), "source": q})

        return keywords, 0.003  # 3 searches

    async def _generate_seo_plan(
        self, niche: str, keywords: list[dict], content_plan: list[str]
    ) -> tuple[dict, float]:
        if not self.settings.anthropic_api_key:
            return {"strategy": "Basic SEO", "keywords": keywords}, 0.0

        import anthropic
        import json

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    f"Create an SEO strategy for a {niche} affiliate site.\n"
                    f"Keywords found: {json.dumps(keywords[:20])}\n"
                    f"Content plan: {json.dumps(content_plan)}\n\n"
                    f"Provide: target_keywords (with intent), internal_linking_plan, "
                    f"meta_tags per page, schema_markup recommendations.\n"
                    f"Return as JSON."
                ),
            }],
        )

        try:
            text = message.content[0].text
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            plan = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            plan = {"raw": message.content[0].text}

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return plan, cost
