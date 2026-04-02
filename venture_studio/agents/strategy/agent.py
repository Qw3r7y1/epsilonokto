"""
Strategy Librarian Agent

Layer 7 — Asset Memory.
Extracts winning patterns from successful experiments and stores
reusable playbooks.

Skills mastered: pattern extraction, playbook templating, success factor
analysis, replication guide authoring, cross-niche generalization.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.db.models import Experiment, ExperimentStatus, Strategy


class StrategyLibrarian(BaseAgent):
    name = "strategy_librarian"
    description = "Extracts actionable playbooks with replication guides, timelines, and scaling plans"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        # Find winning experiments without stored strategies
        result = await self.db.execute(
            select(Experiment).where(
                Experiment.status == ExperimentStatus.winning,
                Experiment.revenue_total > 0,
            )
        )
        winners = result.scalars().all()

        # Check which already have strategies
        existing = await self.db.execute(
            select(Strategy.experiment_id).where(Strategy.experiment_id.isnot(None))
        )
        existing_ids = {row[0] for row in existing.all()}

        new_winners = [w for w in winners if w.id not in existing_ids]
        if not new_winners:
            return AgentResult(success=True, data={"message": "No new winners to process", "strategies_created": 0})

        strategies_created = []
        total_cost = 0.0

        for exp in new_winners:
            playbook, cost = await self._extract_playbook(exp)
            total_cost += cost

            roi = (exp.revenue_total / exp.budget_spent - 1) if exp.budget_spent > 0 else 0.0
            strategy = Strategy(
                experiment_id=exp.id,
                title=f"Playbook: {exp.title}",
                pod=exp.pod,
                niche=exp.niche,
                playbook=playbook,
                roi=roi,
            )
            self.db.add(strategy)
            await self.db.flush()
            strategies_created.append({"strategy_id": str(strategy.id), "title": strategy.title, "roi": roi})

        return AgentResult(
            success=True,
            data={"strategies_created": len(strategies_created), "strategies": strategies_created},
            spend_usd=total_cost,
        )

    async def _extract_playbook(self, experiment: Experiment) -> tuple[dict, float]:
        if not self.settings.anthropic_api_key:
            return {
                "niche": experiment.niche,
                "pod": experiment.pod.value,
                "steps": ["Discovered niche", "Built assets", "Published", "Generated revenue"],
                "revenue": experiment.revenue_total,
                "spend": experiment.budget_spent,
            }, 0.0

        import anthropic
        import json

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a SENIOR strategy consultant extracting winning playbooks. "
                    f"Your playbook must be so detailed that ANYONE can replicate the success. "
                    f"Vague advice gets you replaced.\n\n"
                    f"Extract a reusable strategy playbook from this winning experiment:\n\n"
                    f"Title: {experiment.title}\n"
                    f"Niche: {experiment.niche}\n"
                    f"Pod: {experiment.pod.value}\n"
                    f"Revenue: ${experiment.revenue_total:.2f}\n"
                    f"Spend: ${experiment.budget_spent:.2f}\n"
                    f"ROI: {((experiment.revenue_total / experiment.budget_spent - 1) * 100) if experiment.budget_spent > 0 else 0:.1f}%\n"
                    f"Metadata: {json.dumps(experiment.metadata_ or {})}\n\n"
                    f"Create a structured playbook with ALL of the following:\n\n"
                    f"1. **steps** (array): Numbered step-by-step replication guide. "
                    f"Each step must have: action, tools_needed, expected_output, time_estimate\n\n"
                    f"2. **timeline** (object): Estimated days per phase — "
                    f"setup, content_creation, launch, optimization, scaling\n\n"
                    f"3. **tools_required** (array): Specific tools, APIs, and platforms needed "
                    f"with cost estimates\n\n"
                    f"4. **key_decisions** (array): Critical decisions that made this succeed "
                    f"(niche selection, positioning, monetization choice, etc.)\n\n"
                    f"5. **traffic_sources** (array): Where traffic came from, "
                    f"with estimated percentage per source\n\n"
                    f"6. **monetization_method** (string): Detailed description of how money was made\n\n"
                    f"7. **success_factors** (array): What specifically made this work "
                    f"(not generic — specific to this experiment)\n\n"
                    f"8. **risk_factors** (array): What could go wrong and specific mitigations\n\n"
                    f"9. **scaling_plan** (object): How to 10x this — "
                    f"adjacent_niches, increased_budget_allocation, new_traffic_sources\n\n"
                    f"10. **budget_breakdown** (object): Cost per step/phase\n\n"
                    f"11. **lessons_learned** (array): What worked, what didn't, what to do differently\n\n"
                    f"12. **variation_niches** (array): 3-5 adjacent niches this playbook could be applied to\n\n"
                    f"13. **replication_difficulty** (string): 'easy' | 'moderate' | 'hard' with reasoning\n\n"
                    f"Return as JSON object."
                ),
            }],
        )

        try:
            text = message.content[0].text
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            playbook = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            playbook = {"raw": message.content[0].text}

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return playbook, cost
