"""
Email / CRM Agent

Layer 4 — Distribution.
Manages email sequences and subscriber lifecycle.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class EmailCRMAgent(BaseAgent):
    name = "email_crm"
    description = "Manages email sequences and lead nurture flows"

    async def execute(self, context: dict[str, Any]) -> AgentResult:
        niche = context.get("niche", "")
        offer = context.get("offer", {})

        if not niche:
            return AgentResult(success=False, error="No niche provided")

        sequence, cost = await self._create_email_sequence(niche, offer)

        return AgentResult(
            success=True,
            data={"email_sequence": sequence},
            spend_usd=cost,
        )

    async def _create_email_sequence(
        self, niche: str, offer: dict
    ) -> tuple[list[dict], float]:
        if not self.settings.anthropic_api_key:
            return [
                {"day": 1, "subject": f"Welcome to our {niche} guide", "type": "welcome"},
                {"day": 3, "subject": f"Top {niche} picks", "type": "value"},
                {"day": 7, "subject": f"Don't miss these {niche} deals", "type": "cta"},
            ], 0.0

        import anthropic
        import json

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": (
                    f"Create a 7-email welcome sequence for a {niche} site.\n"
                    f"Offer: {json.dumps(offer)}\n\n"
                    f"Each email needs: day, subject, preview_text, body_outline, cta, email_type.\n"
                    f"Mix value emails (80%) with promotional (20%).\n"
                    f"Return as JSON array."
                ),
            }],
        )

        try:
            text = message.content[0].text
            if "```" in text:
                text = text.split("```json")[-1].split("```")[0] if "```json" in text else text.split("```")[1].split("```")[0]
            sequence = json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            sequence = [{"raw": message.content[0].text}]

        cost = (message.usage.input_tokens * 0.003 + message.usage.output_tokens * 0.015) / 1000
        return sequence, cost
