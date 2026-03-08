"""
Governance Policies

Static policy definitions: prohibited topics, domain whitelists,
and content filters.
"""

from __future__ import annotations

# Topics the system must never create content about
PROHIBITED_TOPICS: set[str] = {
    "gambling",
    "weapons",
    "drugs",
    "adult content",
    "hate speech",
    "violence",
    "terrorism",
    "child exploitation",
    "financial fraud",
    "identity theft",
    "phishing",
    "malware",
    "counterfeit goods",
}

# Domains we are allowed to deploy to
DOMAIN_WHITELIST: set[str] = {
    "*.pages.dev",
    "*.workers.dev",
    "*.vercel.app",
    "*.netlify.app",
}

# Maximum number of API calls per agent per hour
RATE_LIMITS: dict[str, int] = {
    "opportunity_scout": 10,
    "competitor_mapper": 20,
    "offer_architect": 10,
    "builder": 5,
    "publisher": 10,
    "seo_operator": 15,
    "media_engine": 10,
    "email_crm": 5,
    "revenue_collector": 30,
    "capital_allocator": 5,
    "strategy_librarian": 5,
    "governance_controller": 60,
    "agent_architect": 3,
}


def is_topic_prohibited(text: str) -> bool:
    """Check if text contains prohibited topics."""
    text_lower = text.lower()
    return any(topic in text_lower for topic in PROHIBITED_TOPICS)
