"""
Competitor Mapper Agent

Layer 2 — Intelligence.
Analyzes competitors in a given niche to find gaps and positioning angles.

Skills mastered: SerpAPI multi-query analysis, traffic estimation,
tech stack detection, monetization reverse-engineering, content gap matrix.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class CompetitorMapper(BaseAgent):
    name = "competitor_mapper"
    description = "Maps competitor landscape with deep analysis of gaps, traffic, and monetization models"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        niche = context.get("niche", "")
        experiment_id = context.get("experiment_id")

        if not niche:
            return AgentResult(success=False, error="No niche provided")

        # Step 1: Search for competitors — multi-query for thorough coverage
        competitors, search_cost = await self._find_competitors(niche)

        # Step 2: Analyze gaps with Claude — expert-level analysis
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

        queries = [
            f"best {niche} sites reviews 2026",
            f"{niche} alternatives comparison",
            f"top {niche} tools platforms",
        ]
        all_competitors = []
        seen_urls: set[str] = set()

        async with httpx.AsyncClient() as client:
            for query in queries:
                resp = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": self.settings.serpapi_key,
                        "engine": "google",
                        "num": 15,
                    },
                    timeout=30,
                )
                resp.raise_for_status()
                data = resp.json()

                for item in data.get("organic_results", []):
                    url = item.get("link", "")
                    if url and url not in seen_urls:
                        seen_urls.add(url)
                        all_competitors.append({
                            "title": item.get("title", ""),
                            "url": url,
                            "snippet": item.get("snippet", ""),
                            "position": item.get("position", 0),
                            "query": query,
                        })

        return all_competitors, 0.003  # 3 searches

    async def _analyze_gaps(
        self, niche: str, competitors: list[dict]
    ) -> tuple[dict, float]:
        if not self.settings.anthropic_api_key or not competitors:
            return {"gaps": [], "positioning": "Insufficient data"}, 0.0

        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        comp_text = "\n".join(
            f"- [{c['position']}] {c['title']} ({c['url']}): {c['snippet']}"
            for c in competitors[:20]
        )

        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a SENIOR competitive intelligence analyst. "
                    f"Your analysis must be exhaustive and actionable — half-measures get you replaced.\n\n"
                    f"Analyze the competitor landscape for: {niche}\n\n"
                    f"Competitors found (position = SERP ranking):\n{comp_text}\n\n"
                    f"Deliver ALL of the following analyses:\n\n"
                    f"1. **gaps** (array): Market gaps with specific descriptions and opportunity size\n"
                    f"2. **positioning** (string): Recommended unique positioning angle with reasoning\n"
                    f"3. **content_angles** (array): Underserved content topics competitors miss\n"
                    f"4. **weaknesses** (array): Specific competitor weaknesses to exploit\n"
                    f"5. **traffic_estimates** (object): Per-competitor traffic tier "
                    f"('high' >100K/mo, 'medium' 10-100K, 'low' <10K) based on SERP signals\n"
                    f"6. **tech_stacks** (object): Detected tech/platform per competitor "
                    f"(WordPress, Shopify, custom, etc. — infer from URL patterns and snippets)\n"
                    f"7. **monetization_models** (object): Per-competitor monetization method "
                    f"(affiliate, ads, subscription, freemium, lead gen — infer from snippets)\n"
                    f"8. **content_gap_matrix** (array): Topics with search demand that NO competitor covers well\n"
                    f"9. **backlink_signals** (object): Domain authority signals based on SERP position "
                    f"(top 3 = high authority, 4-10 = medium, 11+ = low)\n"
                    f"10. **entry_difficulty** (string): 'easy' | 'moderate' | 'hard' with reasoning\n\n"
                    f"Return structured JSON with all 10 keys. Be specific and actionable — "
                    f"generic analysis like 'improve SEO' is unacceptable."
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
