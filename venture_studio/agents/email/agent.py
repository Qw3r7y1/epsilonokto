"""
Email / CRM Agent

Layer 4 — Distribution.
Manages email sequences and subscriber lifecycle.

Skills mastered: behavioral segmentation, drip campaign design,
subject line optimization, deliverability best practices,
trigger-based automation, A/B testing, spam avoidance.
"""

from __future__ import annotations

from typing import Any

from venture_studio.agents.base import AgentResult, BaseAgent


class EmailCRMAgent(BaseAgent):
    name = "email_crm"
    description = "Designs conversion-optimized email sequences with behavioral triggers and A/B testing"

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
                {"day": 2, "subject": f"The #1 mistake {niche} buyers make", "type": "value"},
                {"day": 3, "subject": f"Top {niche} picks (expert tested)", "type": "value"},
                {"day": 5, "subject": f"How to choose the right {niche}", "type": "value"},
                {"day": 7, "subject": f"Our {niche} comparison chart", "type": "value"},
                {"day": 9, "subject": f"Quick question about {niche}", "type": "engagement"},
                {"day": 11, "subject": f"Limited: {niche} deals this week", "type": "promotional"},
                {"day": 14, "subject": f"Your {niche} action plan", "type": "value"},
                {"day": 18, "subject": f"What did you decide on {niche}?", "type": "re_engagement"},
                {"day": 21, "subject": f"Last chance: {niche} exclusive", "type": "cta"},
            ], 0.0

        import anthropic
        import json

        client = anthropic.AsyncAnthropic(api_key=self.settings.anthropic_api_key)
        message = await client.messages.create(
            model=self.settings.claude_model,
            max_tokens=3000,
            messages=[{
                "role": "user",
                "content": (
                    f"You are a SENIOR email marketing strategist with 10+ years experience. "
                    f"Design a sequence that converts — lazy templates get you replaced.\n\n"
                    f"Create a 10-EMAIL welcome/nurture sequence for a {niche} site.\n"
                    f"Offer: {json.dumps(offer)}\n\n"
                    f"MANDATORY REQUIREMENTS:\n\n"
                    f"1. **10 emails minimum** spanning 21 days\n"
                    f"2. **80/20 ratio**: 80% value emails, 20% promotional\n"
                    f"3. **Per email, provide ALL fields**:\n"
                    f"   - day: send day number\n"
                    f"   - subject_a: primary subject line (under 50 chars)\n"
                    f"   - subject_b: A/B variant subject line (different approach)\n"
                    f"   - preview_text: preheader text (under 90 chars)\n"
                    f"   - body_outline: 3-5 bullet structure of email body\n"
                    f"   - cta: specific call-to-action with button text\n"
                    f"   - email_type: welcome | value | educational | social_proof | promotional | re_engagement\n"
                    f"   - trigger: what action triggers this email "
                    f"(signup, open, click, no_open_3_days, etc.)\n"
                    f"   - segment: which subscriber segment receives this "
                    f"(all, engaged, inactive, clicked_product)\n"
                    f"   - send_time: recommended send time and day of week\n\n"
                    f"4. **Deliverability rules**:\n"
                    f"   - No spam trigger words in subject lines\n"
                    f"   - Text-to-image ratio guidance per email\n"
                    f"   - From name recommendation\n\n"
                    f"5. **Include these special sequences**:\n"
                    f"   - Re-engagement flow: for subscribers who haven't opened in 7 days\n"
                    f"   - Social proof email: featuring testimonials/results\n\n"
                    f"Return as JSON array of email objects."
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
