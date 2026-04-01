"""
Governance Policies

Static policy definitions: prohibited topics, domain whitelists,
content filters, performance standards, and required skill sets.

Every agent must meet performance standards or face replacement.
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

# ── Performance Standards ─────────────────────────────────────────────
# Agents below these thresholds get flagged for review/replacement.

PERFORMANCE_STANDARDS: dict[str, dict] = {
    "opportunity_scout": {
        "min_success_rate": 0.75,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 8,
        "max_cost_per_run_usd": 0.10,
        "kpi_fields": ["opportunities"],
    },
    "competitor_mapper": {
        "min_success_rate": 0.75,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 8,
        "max_cost_per_run_usd": 0.08,
        "kpi_fields": ["competitors", "analysis"],
    },
    "offer_architect": {
        "min_success_rate": 0.70,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 8,
        "max_cost_per_run_usd": 0.10,
        "kpi_fields": ["offer"],
    },
    "builder": {
        "min_success_rate": 0.70,
        "min_runs_before_review": 8,
        "max_consecutive_failures_before_replacement": 5,
        "max_cost_per_run_usd": 0.50,
        "kpi_fields": ["assets"],
    },
    "publisher": {
        "min_success_rate": 0.60,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 10,
        "max_cost_per_run_usd": 0.05,
        "kpi_fields": ["published"],
    },
    "seo_operator": {
        "min_success_rate": 0.75,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 8,
        "max_cost_per_run_usd": 0.10,
        "kpi_fields": ["keywords", "recommendations"],
    },
    "media_engine": {
        "min_success_rate": 0.70,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 8,
        "max_cost_per_run_usd": 0.08,
        "kpi_fields": ["social_content"],
    },
    "email_crm": {
        "min_success_rate": 0.70,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 8,
        "max_cost_per_run_usd": 0.08,
        "kpi_fields": ["email_sequence"],
    },
    "revenue_collector": {
        "min_success_rate": 0.60,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 10,
        "max_cost_per_run_usd": 0.01,
        "kpi_fields": ["total_revenue", "events_processed"],
    },
    "capital_allocator": {
        "min_success_rate": 0.75,
        "min_runs_before_review": 8,
        "max_consecutive_failures_before_replacement": 5,
        "max_cost_per_run_usd": 0.01,
        "kpi_fields": ["allocations"],
    },
    "strategy_librarian": {
        "min_success_rate": 0.70,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 8,
        "max_cost_per_run_usd": 0.10,
        "kpi_fields": ["strategies_created"],
    },
    "governance_controller": {
        "min_success_rate": 0.80,
        "min_runs_before_review": 5,
        "max_consecutive_failures_before_replacement": 3,
        "max_cost_per_run_usd": 0.01,
        "kpi_fields": ["budget", "agent_health"],
    },
    "agent_architect": {
        "min_success_rate": 0.60,
        "min_runs_before_review": 5,
        "max_consecutive_failures_before_replacement": 5,
        "max_cost_per_run_usd": 0.50,
        "kpi_fields": ["proposals"],
    },
}

# ── Required Skills per Agent ─────────────────────────────────────────
# Each agent must master these tools, APIs, and techniques.
# Agents that don't leverage their full skill set are underperforming.

REQUIRED_SKILLS: dict[str, dict] = {
    "opportunity_scout": {
        "apis": ["serpapi", "google_trends", "anthropic_claude"],
        "techniques": [
            "multi_source_trend_validation",
            "tam_sam_som_estimation",
            "competition_density_scoring",
            "seasonality_detection",
            "keyword_demand_analysis",
        ],
        "programs": ["httpx", "json_parsing", "statistical_scoring"],
        "output_standards": [
            "score_every_opportunity_0_to_1",
            "include_hypothesis_per_opportunity",
            "estimate_revenue_potential",
            "assess_competition_level",
            "validate_across_multiple_queries",
        ],
    },
    "competitor_mapper": {
        "apis": ["serpapi", "anthropic_claude"],
        "techniques": [
            "serp_feature_analysis",
            "content_gap_identification",
            "backlink_profile_estimation",
            "tech_stack_detection",
            "monetization_reverse_engineering",
            "traffic_estimation",
        ],
        "programs": ["httpx", "json_parsing", "competitive_frameworks"],
        "output_standards": [
            "map_min_10_competitors",
            "identify_3_plus_gaps",
            "provide_positioning_angles",
            "estimate_traffic_ranges",
            "analyze_monetization_models",
        ],
    },
    "offer_architect": {
        "apis": ["anthropic_claude"],
        "techniques": [
            "conversion_funnel_design",
            "pricing_psychology",
            "value_ladder_construction",
            "a_b_test_planning",
            "usp_formulation",
            "audience_segmentation",
        ],
        "programs": ["json_parsing", "funnel_frameworks"],
        "output_standards": [
            "complete_offer_with_all_fields",
            "realistic_conversion_estimates",
            "multi_monetization_streams",
            "content_plan_with_5_plus_pages",
            "clear_value_proposition",
        ],
    },
    "builder": {
        "apis": ["anthropic_claude"],
        "techniques": [
            "seo_content_writing",
            "e_e_a_t_optimization",
            "conversion_copywriting",
            "structured_data_markup",
            "internal_linking_strategy",
            "above_the_fold_optimization",
        ],
        "programs": ["json_parsing", "markdown_generation", "html_structure"],
        "output_standards": [
            "min_2000_words_per_page",
            "proper_heading_hierarchy",
            "natural_cta_placements",
            "meta_descriptions_under_160_chars",
            "faq_schema_ready",
            "mobile_first_content",
        ],
    },
    "publisher": {
        "apis": ["cloudflare_r2", "boto3_s3"],
        "techniques": [
            "cdn_optimization",
            "asset_versioning",
            "cache_header_configuration",
            "content_type_management",
        ],
        "programs": ["boto3", "json_serialization"],
        "output_standards": [
            "all_assets_uploaded_verified",
            "storage_keys_recorded",
            "is_live_flags_set",
            "zero_data_loss",
        ],
    },
    "seo_operator": {
        "apis": ["serpapi", "anthropic_claude"],
        "techniques": [
            "keyword_clustering",
            "search_intent_classification",
            "topical_authority_mapping",
            "technical_seo_audit",
            "serp_feature_targeting",
            "internal_link_architecture",
            "schema_markup_implementation",
        ],
        "programs": ["httpx", "json_parsing", "seo_frameworks"],
        "output_standards": [
            "keyword_map_with_intent",
            "internal_linking_plan",
            "schema_markup_per_page",
            "meta_tags_optimized",
            "content_gap_priorities",
        ],
    },
    "media_engine": {
        "apis": ["anthropic_claude"],
        "techniques": [
            "hook_formula_frameworks",
            "platform_specific_optimization",
            "hashtag_strategy",
            "engagement_bait_patterns",
            "content_repurposing",
            "viral_loop_design",
            "posting_schedule_optimization",
        ],
        "programs": ["json_parsing", "content_calendaring"],
        "output_standards": [
            "14_day_content_calendar",
            "min_4_platforms_covered",
            "hooks_under_3_seconds",
            "hashtag_strategy_per_post",
            "cta_variety_not_repetitive",
            "platform_native_formatting",
        ],
    },
    "email_crm": {
        "apis": ["anthropic_claude"],
        "techniques": [
            "behavioral_segmentation",
            "drip_campaign_design",
            "subject_line_optimization",
            "deliverability_best_practices",
            "trigger_based_automation",
            "a_b_test_planning",
            "spam_score_avoidance",
        ],
        "programs": ["json_parsing", "email_frameworks"],
        "output_standards": [
            "10_email_minimum_sequence",
            "80_20_value_promo_ratio",
            "subject_lines_under_50_chars",
            "preview_text_optimized",
            "behavioral_triggers_defined",
            "unsubscribe_compliance",
        ],
    },
    "revenue_collector": {
        "apis": ["stripe", "webhook_processing"],
        "techniques": [
            "revenue_attribution",
            "multi_source_reconciliation",
            "anomaly_detection",
            "currency_normalization",
            "duplicate_event_detection",
        ],
        "programs": ["stripe_sdk", "sqlalchemy", "datetime_handling"],
        "output_standards": [
            "accurate_amount_recording",
            "source_attribution_per_event",
            "experiment_revenue_updated",
            "daily_outcome_snapshot_created",
            "zero_duplicate_events",
        ],
    },
    "capital_allocator": {
        "apis": ["database_queries"],
        "techniques": [
            "thompson_sampling",
            "multi_armed_bandit",
            "roi_calculation",
            "risk_adjusted_scoring",
            "portfolio_rebalancing",
            "exploration_vs_exploitation",
        ],
        "programs": ["sqlalchemy", "statistical_methods"],
        "output_standards": [
            "allocations_sum_to_budget",
            "roi_scored_per_experiment",
            "underperformers_killed",
            "exploration_bonus_for_new",
            "allocation_recorded_in_ledger",
        ],
    },
    "strategy_librarian": {
        "apis": ["anthropic_claude"],
        "techniques": [
            "pattern_extraction",
            "playbook_templating",
            "success_factor_analysis",
            "replication_guide_authoring",
            "cross_niche_generalization",
        ],
        "programs": ["json_parsing", "sqlalchemy"],
        "output_standards": [
            "structured_playbook_json",
            "replication_guide_included",
            "success_factors_identified",
            "traffic_sources_documented",
            "roi_recorded",
        ],
    },
    "governance_controller": {
        "apis": ["database_queries"],
        "techniques": [
            "budget_auditing",
            "agent_health_monitoring",
            "circuit_breaker_management",
            "compliance_scanning",
            "performance_review",
            "replacement_recommendation",
        ],
        "programs": ["sqlalchemy", "statistical_methods"],
        "output_standards": [
            "complete_health_report",
            "budget_utilization_tracked",
            "underperformers_flagged",
            "replacement_candidates_identified",
            "content_compliance_verified",
        ],
    },
    "agent_architect": {
        "apis": ["anthropic_claude"],
        "techniques": [
            "capability_gap_analysis",
            "agent_code_generation",
            "proposal_validation",
            "performance_based_cleanup",
            "tier_classification",
        ],
        "programs": ["anthropic_sdk", "code_generation", "sqlalchemy"],
        "output_standards": [
            "validated_proposals_only",
            "generated_code_inherits_base",
            "cost_estimates_realistic",
            "failed_agents_disabled",
            "replacement_agents_proposed",
        ],
    },
}


def is_topic_prohibited(text: str) -> bool:
    """Check if text contains prohibited topics."""
    text_lower = text.lower()
    return any(topic in text_lower for topic in PROHIBITED_TOPICS)


def get_performance_standard(agent_name: str) -> dict:
    """Get performance standards for an agent. Returns defaults if not found."""
    return PERFORMANCE_STANDARDS.get(agent_name, {
        "min_success_rate": 0.70,
        "min_runs_before_review": 10,
        "max_consecutive_failures_before_replacement": 5,
        "max_cost_per_run_usd": 0.50,
        "kpi_fields": [],
    })


def get_required_skills(agent_name: str) -> dict:
    """Get required skills for an agent."""
    return REQUIRED_SKILLS.get(agent_name, {
        "apis": [],
        "techniques": [],
        "programs": [],
        "output_standards": [],
    })
