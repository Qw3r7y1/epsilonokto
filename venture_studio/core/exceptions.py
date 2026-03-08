"""Venture Studio exception hierarchy."""

from __future__ import annotations


class VentureError(Exception):
    """Base exception for all venture studio errors."""


class KillSwitchActive(VentureError):
    """Raised when the global kill switch is on."""


class BudgetExceeded(VentureError):
    """Raised when a spend limit is breached."""


class AgentDisabled(VentureError):
    """Raised when an agent that is disabled tries to execute."""


class CircuitBreakerOpen(VentureError):
    """Raised when an agent has exceeded its failure threshold."""


class GovernanceViolation(VentureError):
    """Raised on policy violation (prohibited topic, blocked domain, etc.)."""
