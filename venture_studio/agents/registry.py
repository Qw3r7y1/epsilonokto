"""
Agent Registry

Central registry of all venture studio agents.
Lazily imports to avoid circular dependencies.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from venture_studio.agents.base import BaseAgent

# Maps agent name → module path, class name
_AGENT_MAP: dict[str, tuple[str, str]] = {
    "opportunity_scout": ("venture_studio.agents.scout.agent", "OpportunityScout"),
    "competitor_mapper": ("venture_studio.agents.competitor.agent", "CompetitorMapper"),
    "offer_architect": ("venture_studio.agents.offer.agent", "OfferArchitect"),
    "builder": ("venture_studio.agents.builder.agent", "BuilderAgent"),
    "publisher": ("venture_studio.agents.publisher.agent", "PublisherAgent"),
    "seo_operator": ("venture_studio.agents.seo.agent", "SEOOperator"),
    "media_engine": ("venture_studio.agents.media.agent", "MediaEngine"),
    "email_crm": ("venture_studio.agents.email.agent", "EmailCRMAgent"),
    "revenue_collector": ("venture_studio.agents.revenue.agent", "RevenueCollector"),
    "capital_allocator": ("venture_studio.agents.capital.agent", "CapitalAllocator"),
    "strategy_librarian": ("venture_studio.agents.strategy.agent", "StrategyLibrarian"),
    "governance_controller": ("venture_studio.agents.governance.agent", "GovernanceAgent"),
    "agent_architect": ("venture_studio.agents.architect.agent", "AgentArchitect"),
}

AGENT_REGISTRY: dict[str, type] = {}


def _import_agent(module_path: str, class_name: str) -> type:
    import importlib
    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


def get_agent(name: str) -> type:
    """Get an agent class by name, importing lazily."""
    if name not in AGENT_REGISTRY:
        if name not in _AGENT_MAP:
            raise ValueError(f"Unknown agent: {name}")
        module_path, class_name = _AGENT_MAP[name]
        AGENT_REGISTRY[name] = _import_agent(module_path, class_name)
    return AGENT_REGISTRY[name]


def all_agent_names() -> list[str]:
    return list(_AGENT_MAP.keys())
