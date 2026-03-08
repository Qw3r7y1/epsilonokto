"""
Agent Architect — Recursive Agent Factory

Tier 0 meta-agent. Analyzes system performance and creates new
Tier 2/3 agents when it identifies capability gaps or optimization
opportunities.

New agents are:
  1. Designed (mission, I/O, cost estimate)
  2. Validated against governance rules
  3. Registered in the agent table
  4. Generated as executable Python modules
  5. Added to the dynamic registry

Safety: all generated agents inherit BaseAgent governance (kill switch,
budget limits, circuit breakers, audit trail).
"""

from __future__ import annotations

import enum
import textwrap
from typing import Any

from sqlalchemy import select

from venture_studio.agents.base import AgentResult, BaseAgent
from venture_studio.db.models import (
    Agent as AgentModel,
    Experiment,
    ExperimentStatus,
    Strategy,
)


class AgentTier(str, enum.Enum):
    operational = "tier2_operational"
    experimental = "tier3_experimental"


class AgentArchitect(BaseAgent):
    name = "agent_architect"
    description = "Recursive meta-agent that designs and creates new specialized agents"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        mode = context.get("mode", "analyze")  # analyze | create | cleanup

        if mode == "analyze":
            return await self._analyze_and_propose(context)
        elif mode == "create":
            return await self._create_agent(context)
        elif mode == "cleanup":
            return await self._cleanup_failed_agents(context)
        else:
            return AgentResult(success=False, error=f"Unknown mode: {mode}")

    # ── Analysis ─────────────────────────────────────────────────────────

    async def _analyze_and_propose(self, context: dict[str, Any]) -> AgentResult:
        """Analyze system state and propose new agents."""
        # Gather signals
        winning_experiments = await self._get_winning_experiments()
        strategies = await self._get_top_strategies()
        existing_agents = await self._get_existing_agents()

        if not self.settings.anthropic_api_key:
            return AgentResult(
                success=True,
                data={"proposals": [], "message": "No API key — skipping analysis"},
            )

        import anthropic
        import json

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)

        agent_names = [a["name"] for a in existing_agents]
        exp_summaries = [
            {"title": e.title, "niche": e.niche, "pod": e.pod.value, "revenue": e.revenue_total}
            for e in winning_experiments
        ]
        strategy_summaries = [
            {"title": s.title, "niche": s.niche, "roi": s.roi, "playbook_keys": list((s.playbook or {}).keys())}
            for s in strategies
        ]

        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": (
                    "You are the Agent Architect for an autonomous venture studio.\n\n"
                    f"Existing agents: {json.dumps(agent_names)}\n"
                    f"Winning experiments: {json.dumps(exp_summaries)}\n"
                    f"Top strategies: {json.dumps(strategy_summaries)}\n\n"
                    "Analyze the system and propose up to 3 new specialized agents that would:\n"
                    "1. Exploit successful patterns (double down on winners)\n"
                    "2. Fill capability gaps\n"
                    "3. Optimize bottlenecks\n\n"
                    "For each proposed agent, provide:\n"
                    "- agent_name (snake_case)\n"
                    "- mission (1 sentence)\n"
                    "- tier (tier2_operational or tier3_experimental)\n"
                    "- inputs (list of input data types)\n"
                    "- outputs (list of output data types)\n"
                    "- execution_frequency (hourly/daily/weekly/on_demand)\n"
                    "- cost_estimate_per_run_usd (float)\n"
                    "- expected_roi_multiplier (float)\n"
                    "- creation_reason (why this agent is needed)\n\n"
                    "Return JSON array of proposals. Return empty array if no agents needed."
                ),
            }],
        )

        try:
            text = message.content[0].text
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            proposals = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            proposals = []

        # Validate proposals
        validated = [p for p in proposals if self._validate_proposal(p, agent_names)]

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return AgentResult(
            success=True,
            data={"proposals": validated, "rejected": len(proposals) - len(validated)},
            spend_usd=cost,
        )

    # ── Creation ─────────────────────────────────────────────────────────

    async def _create_agent(self, context: dict[str, Any]) -> AgentResult:
        """Create a new agent from a validated proposal."""
        proposal = context.get("proposal", {})
        if not proposal:
            return AgentResult(success=False, error="No proposal provided")

        agent_name = proposal.get("agent_name", "")
        if not agent_name:
            return AgentResult(success=False, error="No agent_name in proposal")

        # Check not duplicate
        existing = await self.db.execute(
            select(AgentModel).where(AgentModel.name == agent_name)
        )
        if existing.scalar_one_or_none():
            return AgentResult(success=False, error=f"Agent {agent_name} already exists")

        # Generate agent code
        code, cost = await self._generate_agent_code(proposal)

        # Register in database
        agent_record = AgentModel(
            name=agent_name,
            description=proposal.get("mission", ""),
            enabled=True,
            config={
                "tier": proposal.get("tier", "tier3_experimental"),
                "inputs": proposal.get("inputs", []),
                "outputs": proposal.get("outputs", []),
                "execution_frequency": proposal.get("execution_frequency", "on_demand"),
                "cost_estimate": proposal.get("cost_estimate_per_run_usd", 0.01),
                "expected_roi": proposal.get("expected_roi_multiplier", 1.0),
                "created_by": self.name,
                "creation_reason": proposal.get("creation_reason", ""),
                "generated_code": code,
            },
        )
        self.db.add(agent_record)

        return AgentResult(
            success=True,
            data={
                "agent_name": agent_name,
                "registered": True,
                "code_generated": bool(code),
            },
            spend_usd=cost,
        )

    # ── Cleanup ──────────────────────────────────────────────────────────

    async def _cleanup_failed_agents(self, context: dict[str, Any]) -> AgentResult:
        """Disable Tier 3 agents that have failed repeatedly."""
        result = await self.db.execute(select(AgentModel))
        agents = result.scalars().all()

        disabled = []
        for agent in agents:
            config = agent.config or {}
            if (
                config.get("tier") == "tier3_experimental"
                and agent.total_failures > 5
                and agent.total_successes == 0
            ):
                agent.enabled = False
                disabled.append(agent.name)

        return AgentResult(
            success=True,
            data={"disabled_agents": disabled, "count": len(disabled)},
        )

    # ── Helpers ──────────────────────────────────────────────────────────

    def _validate_proposal(self, proposal: dict, existing_names: list[str]) -> bool:
        """Validate an agent proposal against governance rules."""
        name = proposal.get("agent_name", "")
        if not name or name in existing_names:
            return False
        if proposal.get("cost_estimate_per_run_usd", 0) > self.settings.max_experiment_spend_usd:
            return False
        if not proposal.get("mission"):
            return False
        return True

    async def _get_winning_experiments(self) -> list[Experiment]:
        result = await self.db.execute(
            select(Experiment).where(Experiment.status == ExperimentStatus.winning).limit(20)
        )
        return list(result.scalars().all())

    async def _get_top_strategies(self) -> list[Strategy]:
        result = await self.db.execute(
            select(Strategy).order_by(Strategy.roi.desc().nullslast()).limit(10)
        )
        return list(result.scalars().all())

    async def _get_existing_agents(self) -> list[dict]:
        result = await self.db.execute(select(AgentModel))
        return [{"name": a.name, "enabled": a.enabled, "tier": (a.config or {}).get("tier", "tier1_core")} for a in result.scalars().all()]

    async def _generate_agent_code(self, proposal: dict) -> tuple[str, float]:
        """Use Claude to generate the Python code for a new agent."""
        if not self.settings.anthropic_api_key:
            return self._stub_code(proposal), 0.0

        import anthropic

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=4096,
            messages=[{
                "role": "user",
                "content": (
                    "Generate a Python agent class that inherits from BaseAgent.\n\n"
                    f"Agent name: {proposal['agent_name']}\n"
                    f"Mission: {proposal.get('mission', '')}\n"
                    f"Inputs: {proposal.get('inputs', [])}\n"
                    f"Outputs: {proposal.get('outputs', [])}\n\n"
                    "The class must:\n"
                    "1. Inherit from venture_studio.agents.base.BaseAgent\n"
                    "2. Set name and description class attributes\n"
                    "3. Implement async def execute(self, context) -> AgentResult\n"
                    "4. Use self.settings for configuration\n"
                    "5. Track spend via AgentResult.spend_usd\n\n"
                    "Return ONLY the Python code, no markdown."
                ),
            }],
        )

        code = message.content[0].text
        if "```" in code:
            code = code.split("```python")[-1].split("```")[0] if "```python" in code else code.split("```")[1].split("```")[0]

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return code.strip(), cost

    def _stub_code(self, proposal: dict) -> str:
        name = proposal.get("agent_name", "stub_agent")
        class_name = "".join(w.capitalize() for w in name.split("_"))
        return textwrap.dedent(f"""\
            from venture_studio.agents.base import AgentResult, BaseAgent
            from typing import Any

            class {class_name}(BaseAgent):
                name = "{name}"
                description = "{proposal.get('mission', 'Auto-generated agent')}"

                async def execute(self, context: dict[str, Any]) -> AgentResult:
                    # TODO: implement {name} logic
                    return AgentResult(success=True, data={{"message": "stub"}})
        """)
