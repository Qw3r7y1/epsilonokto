"""
Opportunity Scout Agent

Layer 2 — Intelligence.
Discovers trending niches and monetization opportunities using
SerpAPI trend data and Claude analysis.

Outputs: scored opportunity dicts → persisted as Experiment rows.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class OpportunityScout(BaseAgent):
    name = "opportunity_scout"
    description = "Discovers trending niches and scores monetization opportunities"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        pod = context.get("pod", self.settings.active_pod)
        max_results = context.get("max_results", 10)

        # Step 1: Gather trend signals via SerpAPI
        queries = self._build_search_queries(pod)
        raw_trends: list[dict] = []
        spend = 0.0

        for query in queries:
            trends, cost = await self._search_trends(query)
            raw_trends.extend(trends)
            spend += cost

        # Step 2: Score and rank with Claude
        scored, llm_cost = await self._score_opportunities(raw_trends, pod)
        spend += llm_cost

        # Step 3: Return top N
        top = sorted(scored, key=lambda o: o.get("score", 0), reverse=True)[:max_results]

        return AgentResult(success=True, data={"opportunities": top, "total_found": len(scored)}, spend_usd=spend)

    # ── Internal ─────────────────────────────────────────────────────────

    def _build_search_queries(self, pod: str) -> list[str]:
        base_queries = {
            "affiliate": [
                "best affiliate niches 2026",
                "trending products to promote",
                "high commission affiliate programs",
                "rising consumer trends",
            ],
            "digital_product": [
                "digital product ideas trending",
                "online course niches demand",
                "template marketplace trends",
            ],
            "lead_gen": [
                "high value lead generation niches",
                "local business lead gen opportunities",
            ],
            "micro_saas": [
                "micro saas ideas 2026",
                "underserved software niches",
            ],
            "trend_media": [
                "viral content trends",
                "trending topics for content creators",
            ],
        }
        return base_queries.get(pod, base_queries["affiliate"])

    async def _search_trends(self, query: str) -> tuple[list[dict], float]:
        """Call SerpAPI for trend data. Returns (results, cost_usd)."""
        if not self.settings.serpapi_key:
            # Stub: return empty when no key configured
            return [], 0.0

        import httpx

        async with httpx.AsyncClient() as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": query,
                    "api_key": self.settings.serpapi_key,
                    "engine": "google",
                    "num": 20,
                },
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()

        results = []
        for item in data.get("organic_results", []):
            results.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "link": item.get("link", ""),
                "query": query,
            })
        # SerpAPI costs ~$0.001/search
        return results, 0.001

    async def _score_opportunities(
        self, trends: list[dict], pod: str
    ) -> tuple[list[dict], float]:
        """Use Claude to score and structure opportunities."""
        if not self.settings.anthropic_api_key or not trends:
            # Return unscored if no API key
            return [{"title": t["title"], "niche": t.get("query", ""), "score": 0.5, "source": t} for t in trends], 0.0

        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        trend_text = "\n".join(f"- {t['title']}: {t['snippet']}" for t in trends[:30])

        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=self.settings.claude_max_tokens,
            messages=[{
                "role": "user",
                "content": (
                    f"You are an opportunity analyst for a {pod} venture studio.\n\n"
                    f"Analyze these trend signals and extract distinct business opportunities.\n"
                    f"For each opportunity, provide: title, niche, score (0-1), hypothesis, "
                    f"estimated_competition (low/medium/high), estimated_revenue_potential (low/medium/high).\n\n"
                    f"Trend signals:\n{trend_text}\n\n"
                    f"Return a JSON array of opportunity objects."
                ),
            }],
        )

        import json
        text = message.content[0].text
        # Try to extract JSON from the response
        try:
            # Handle markdown code blocks
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            opportunities = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            opportunities = [{"title": t["title"], "niche": t.get("query", ""), "score": 0.5} for t in trends]

        # Estimate cost: ~$0.003/1K input tokens, ~$0.015/1K output tokens (Sonnet)
        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return opportunities, cost
