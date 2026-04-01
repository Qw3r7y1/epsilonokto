"""
SEO Operator Agent

Layer 4 — Distribution.
Handles keyword research, on-page SEO optimization, and indexing.

Skills mastered: keyword clustering, search intent classification,
topical authority mapping, technical SEO, SERP feature targeting,
internal link architecture, schema markup implementation.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class SEOOperator(BaseAgent):
    name = "seo_operator"
    description = "Performs expert keyword research, intent mapping, and full-stack SEO optimization"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        niche = context.get("niche", "")
        content_plan = context.get("content_plan", [])

        if not niche:
            return AgentResult(success=False, error="No niche provided")

        # Step 1: Keyword research — multi-intent coverage
        keywords, search_cost = await self._keyword_research(niche)

        # Step 2: Generate SEO recommendations — expert-level
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
        queries = [
            f"best {niche}",                    # commercial intent
            f"{niche} reviews",                  # commercial investigation
            f"{niche} guide",                    # informational
            f"{niche} vs",                       # comparison intent
            f"{niche} how to",                   # informational/tutorial
        ]

        async with httpx.AsyncClient() as client:
            for q in queries:
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

                # Capture related searches
                for r in data.get("related_searches", []):
                    keywords.append({
                        "keyword": r.get("query", ""),
                        "source": q,
                        "type": "related_search",
                    })

                # Capture People Also Ask for FAQ schema opportunities
                for paa in data.get("related_questions", []):
                    keywords.append({
                        "keyword": paa.get("question", ""),
                        "source": q,
                        "type": "people_also_ask",
                    })

        return keywords, 0.005  # 5 searches

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
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a SENIOR SEO strategist who has ranked 100+ sites to page 1. "
                    f"Deliver a complete SEO blueprint — anything generic gets you replaced.\n\n"
                    f"Niche: {niche}\n"
                    f"Keywords found: {json.dumps(keywords[:30])}\n"
                    f"Content plan: {json.dumps(content_plan)}\n\n"
                    f"Deliver ALL of the following:\n\n"
                    f"1. **target_keywords** (array): Each with: keyword, search_intent "
                    f"(informational/commercial/transactional/navigational), "
                    f"estimated_difficulty (1-10), target_page (which content_plan page)\n\n"
                    f"2. **topical_authority_map** (object): Pillar page + cluster pages structure. "
                    f"Show how pages interlink to build topical authority\n\n"
                    f"3. **internal_linking_plan** (array): Specific anchor text + source page → target page pairs\n\n"
                    f"4. **meta_tags** (object): Per content_plan page: title tag (under 60 chars), "
                    f"meta description (under 160 chars), primary keyword, secondary keywords\n\n"
                    f"5. **schema_markup** (object): Per page: recommended schema types "
                    f"(Article, FAQ, HowTo, Product, Review) with key properties\n\n"
                    f"6. **serp_feature_targets** (array): Which SERP features to target "
                    f"(featured snippets, PAA, knowledge panels) and how\n\n"
                    f"7. **technical_seo_checklist** (array): Page speed, Core Web Vitals targets, "
                    f"mobile optimization, crawlability requirements\n\n"
                    f"8. **content_gap_priorities** (array): Keywords with demand but no existing "
                    f"content, ranked by opportunity score\n\n"
                    f"Return as JSON object with all 8 keys."
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
