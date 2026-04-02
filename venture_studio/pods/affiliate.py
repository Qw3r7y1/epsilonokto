"""
Pod A — Affiliate Commerce

Configuration and logic specific to the affiliate commerce pod.
This is the first pod to go live.
"""

from __future__ import annotations

# Affiliate networks to integrate with
AFFILIATE_NETWORKS: list[dict] = [
    {"name": "Amazon Associates", "commission_range": "1-10%", "cookie_days": 1},
    {"name": "ShareASale", "commission_range": "5-50%", "cookie_days": 30},
    {"name": "CJ Affiliate", "commission_range": "3-50%", "cookie_days": 30},
    {"name": "Impact", "commission_range": "5-30%", "cookie_days": 30},
    {"name": "Awin", "commission_range": "5-30%", "cookie_days": 30},
]

# Content types this pod produces
CONTENT_TYPES: list[str] = [
    "best-of-list",       # "Best X for Y in 2026"
    "product-review",     # Single product deep-dive
    "comparison",         # "X vs Y"
    "buying-guide",       # "How to choose X"
    "deal-roundup",       # "Best X deals this week"
]

# Minimum requirements for launching an affiliate experiment
LAUNCH_CRITERIA: dict = {
    "min_score": 0.6,
    "min_search_volume_hint": "medium",  # from SerpAPI related searches
    "max_competition_hint": "medium",
    "min_content_pages": 3,
    "max_content_pages": 10,
}
