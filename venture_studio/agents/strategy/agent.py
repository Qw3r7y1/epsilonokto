"""
Strategy Librarian Agent

Layer 7 — Asset Memory.
Extracts winning patterns from successful experiments and stores
reusable playbooks.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.db.models import Experiment, ExperimentStatus, Strategy


class StrategyLibrarian(BaseAgent):
    name = "strategy_librarian"
    description = "Extracts and stores winning strategies from successful experiments"

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
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    f"Extract a reusable strategy playbook from this experiment:\n\n"
                    f"Title: {experiment.title}\n"
                    f"Niche: {experiment.niche}\n"
                    f"Pod: {experiment.pod.value}\n"
                    f"Revenue: ${experiment.revenue_total:.2f}\n"
                    f"Spend: ${experiment.budget_spent:.2f}\n"
                    f"Metadata: {json.dumps(experiment.metadata_ or {})}\n\n"
                    f"Create a structured playbook with: steps, key_decisions, "
                    f"traffic_sources, monetization_method, success_factors, replication_guide.\n"
                    f"Return as JSON."
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
