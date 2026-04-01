"""
Opportunity Scout Agent

Layer 2 — Intelligence.
Discovers trending niches and monetization opportunities using
SerpAPI trend data and Claude analysis.

Skills mastered: SerpAPI, Google Trends analysis, TAM/SAM estimation,
competition density scoring, seasonality detection, keyword demand analysis.

Outputs: scored opportunity dicts → persisted as Experiment rows.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class OpportunityScout(BaseAgent):
    name = "opportunity_scout"
    description = "Discovers trending niches and scores monetization opportunities with expert-level market analysis"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        pod = context.get("pod", self.settings.active_pod)
        max_results = context.get("max_results", 10)

        # Step 1: Gather trend signals via SerpAPI — multi-query validation
        queries = self._build_search_queries(pod)
        raw_trends: list[dict] = []
        spend = 0.0

        for query in queries:
            trends, cost = await self._search_trends(query)
            raw_trends.extend(trends)
            spend += cost

        # Step 2: Score and rank with Claude — expert-level analysis
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
                "trending products to promote 2026",
                "high commission affiliate programs",
                "rising consumer trends ecommerce",
                "underserved affiliate markets low competition",
                "emerging product categories consumer demand",
                "google trends rising categories 2026",
            ],
            "digital_product": [
                "digital product ideas trending 2026",
                "online course niches demand growing",
                "template marketplace trends underserved",
                "info product demand gaps 2026",
                "course platform trending topics",
                "printable digital product niches",
            ],
            "lead_gen": [
                "high value lead generation niches 2026",
                "local business lead gen opportunities",
                "B2B lead generation underserved industries",
                "professional services lead gen high ticket",
                "emerging markets local lead generation",
            ],
            "micro_saas": [
                "micro saas ideas 2026",
                "underserved software niches small business",
                "SaaS tools small teams need 2026",
                "automation tool gaps workflow",
                "niche software problems unsolved",
            ],
            "trend_media": [
                "viral content trends 2026",
                "trending topics for content creators",
                "emerging social media niches underserved",
                "content creator monetization trending",
                "faceless content niches growing",
            ],
        }
        return base_queries.get(pod, base_queries["affiliate"])

    async def _search_trends(self, query: str) -> tuple[list[dict], float]:
        """Call SerpAPI for trend data. Returns (results, cost_usd)."""
        if not self.settings.serpapi_key:
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
        # Also capture related searches for deeper validation
        for related in data.get("related_searches", []):
            results.append({
                "title": related.get("query", ""),
                "snippet": f"Related search signal: {related.get('query', '')}",
                "link": "",
                "query": query,
                "type": "related_search",
            })
        return results, 0.001

    async def _score_opportunities(
        self, trends: list[dict], pod: str
    ) -> tuple[list[dict], float]:
        """Use Claude to score and structure opportunities with expert analysis."""
        if not self.settings.anthropic_api_key or not trends:
            return [{"title": t["title"], "niche": t.get("query", ""), "score": 0.5, "source": t} for t in trends], 0.0

        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        trend_text = "\n".join(f"- {t['title']}: {t['snippet']}" for t in trends[:40])

        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=self.settings.claude_max_tokens,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a SENIOR opportunity analyst for a {pod} venture studio. "
                    f"Your job is on the line — deliver expert-grade analysis or be replaced.\n\n"
                    f"Analyze these trend signals and extract DISTINCT, VALIDATED business opportunities.\n"
                    f"For each opportunity, you MUST provide ALL of the following:\n\n"
                    f"- title: concise opportunity name\n"
                    f"- niche: specific market niche (not generic)\n"
                    f"- score: 0.0-1.0 confidence score based on evidence strength\n"
                    f"- hypothesis: specific testable business hypothesis\n"
                    f"- tam_estimate: total addressable market size estimate (e.g. '$500M', '$2B')\n"
                    f"- competition_density: 1-10 score (1=blue ocean, 10=saturated)\n"
                    f"- seasonality: 'evergreen' | 'seasonal' | 'trending_up' | 'trending_down'\n"
                    f"- monetization_pathways: list of specific monetization methods "
                    f"(e.g. 'Amazon Associates + direct brand deals', not just 'affiliate')\n"
                    f"- audience_size_estimate: estimated reachable audience\n"
                    f"- time_to_revenue_days: realistic estimate\n"
                    f"- validation_sources: how many trend signals support this (cite specifics)\n"
                    f"- confidence_level: 'high' | 'medium' | 'low' with reasoning\n"
                    f"- estimated_revenue_potential: 'low' (<$500/mo) | 'medium' ($500-$5K/mo) | 'high' (>$5K/mo)\n\n"
                    f"RULES:\n"
                    f"- Only include opportunities validated by 2+ trend signals\n"
                    f"- Be specific about niches — 'fitness' is too broad, 'home gym equipment for apartments' is specific\n"
                    f"- Score ruthlessly — most opportunities should be 0.3-0.7, only exceptional ones above 0.8\n"
                    f"- If competition_density > 7, score must be < 0.5 unless there's a clear differentiation angle\n\n"
                    f"Trend signals:\n{trend_text}\n\n"
                    f"Return a JSON array of opportunity objects. Quality over quantity."
                ),
            }],
        )

        import json
        text = message.content[0].text
        try:
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            opportunities = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            opportunities = [{"title": t["title"], "niche": t.get("query", ""), "score": 0.5} for t in trends]

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return opportunities, cost
