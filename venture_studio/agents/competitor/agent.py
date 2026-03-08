"""
Competitor Mapper Agent

Layer 2 — Intelligence.
Analyzes competitors in a given niche to find gaps and positioning angles.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class CompetitorMapper(BaseAgent):
    name = "competitor_mapper"
    description = "Maps competitor landscape for a given niche"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        niche = context.get("niche", "")
        experiment_id = context.get("experiment_id")

        if not niche:
            return AgentResult(success=False, error="No niche provided")

        # Step 1: Search for competitors
        competitors, search_cost = await self._find_competitors(niche)

        # Step 2: Analyze gaps with Claude
        analysis, llm_cost = await self._analyze_gaps(niche, competitors)

        return AgentResult(
            success=True,
            data={
                "niche": niche,
                "competitors": competitors,
                "analysis": analysis,
            },
            spend_usd=search_cost + llm_cost,
        )

    async def _find_competitors(self, niche: str) -> tuple[list[dict], float]:
        if not self.settings.serpapi_key:
            return [], 0.0

        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": f"best {niche} sites reviews",
                    "api_key": self.settings.serpapi_key,
                    "engine": "google",
                    "num": 15,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        competitors = []
        for item in data.get("organic_results", []):
            competitors.append({
                "title": item.get("title", ""),
                "url": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "position": item.get("position", 0),
            })
        return competitors, 0.001

    async def _analyze_gaps(
        self, niche: str, competitors: list[dict]
    ) -> tuple[dict, float]:
        if not self.settings.anthropic_api_key or not competitors:
            return {"gaps": [], "positioning": "Insufficient data"}, 0.0

        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        comp_text = "\n".join(f"- {c['title']} ({c['url']}): {c['snippet']}" for c in competitors[:10])

        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    f"Analyze the competitor landscape for the niche: {niche}\n\n"
                    f"Competitors:\n{comp_text}\n\n"
                    f"Identify:\n1. Market gaps\n2. Underserved audiences\n"
                    f"3. Positioning angles\n4. Content gaps\n5. Monetization weaknesses\n\n"
                    f"Return structured JSON with keys: gaps, positioning, content_angles, weaknesses."
                ),
            }],
        )

        import json
        try:
            text = message.content[0].text
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            analysis = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            analysis = {"raw_analysis": message.content[0].text}

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return analysis, cost
