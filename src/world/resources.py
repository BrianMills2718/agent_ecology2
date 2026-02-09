"""Resource type constants (TD-004).

Canonical names for all resource types used in the simulation.
Use these constants instead of string literals to prevent typos
and enable IDE navigation.

Resource Categories:
- DEPLETABLE: Once spent, gone forever (e.g., llm_budget in dollars)
- ALLOCATABLE: Quota that can be used and reclaimed (e.g., disk bytes)
- RENEWABLE: Rate-limited, replenishes over time (e.g., cpu_seconds per minute)

Terminology (Plan #166 - Resource Rights Model):
- RESOURCE_LLM_BUDGET: Primary LLM constraint in dollars
- RESOURCE_LLM_TOKENS: DEPRECATED - use RESOURCE_LLM_BUDGET instead
  The token-based model conflated usage tracking with rights/quotas.
  Dollar budget is the single constraint; per-model tracking is handled separately.

Future (Plan #166 Phase 3+): Resources will become tradeable artifacts.
"""

# === Depletable Resources (stock, finite) ===
# Once spent, these are gone - scarcity drives behavior

RESOURCE_LLM_BUDGET = "llm_budget"
"""LLM budget in dollars. Primary constraint for LLM usage (Plan #153).

This is THE constraint on LLM usage. Agents spend their dollar budget on LLM
calls. When budget is exhausted, no more LLM calls are allowed.
"""

# === Allocatable Resources (quota, reclaimable) ===
# Agents have a quota; usage can be reclaimed (e.g., deleting artifacts)

RESOURCE_DISK = "disk"
"""Disk storage in bytes. Artifacts consume disk; deletion reclaims it."""

# === Renewable Resources (rate-limited) ===
# Replenishes over time via token bucket / rolling windows

RESOURCE_LLM_TOKENS = "llm_tokens"
"""DEPRECATED (Plan #166): LLM tokens as a resource concept.

This conflated multiple concerns:
- Usage tracking (how many tokens were consumed)
- Rate limiting (tokens per window)
- Budget constraint (total tokens allowed)

Migration path:
- For cost constraint: Use RESOURCE_LLM_BUDGET (dollar-based)
- For rate limiting: Use per-model rate limits in config
- For usage tracking: Use UsageTracker (Plan #166 Phase 2)

Will be removed in a future version. Code using this should migrate
to dollar-based budget constraint (RESOURCE_LLM_BUDGET).
"""

RESOURCE_CPU = "cpu_seconds"
"""CPU time in seconds per period."""

# === All Resources ===

ALL_RESOURCES = frozenset({
    RESOURCE_LLM_BUDGET,
    RESOURCE_DISK,
    RESOURCE_LLM_TOKENS,
    RESOURCE_CPU,
})
"""Set of all canonical resource names."""

DEPLETABLE_RESOURCES = frozenset({
    RESOURCE_LLM_BUDGET,
})
"""Resources that are consumed and never replenish."""

ALLOCATABLE_RESOURCES = frozenset({
    RESOURCE_DISK,
})
"""Resources with quotas that can be reclaimed."""

RENEWABLE_RESOURCES = frozenset({
    RESOURCE_LLM_TOKENS,
    RESOURCE_CPU,
})
"""Resources that replenish over time (rate-limited)."""


__all__ = [
    # Primary resources
    "RESOURCE_LLM_BUDGET",
    "RESOURCE_DISK",
    "RESOURCE_LLM_TOKENS",
    "RESOURCE_CPU",
    # Collections
    "ALL_RESOURCES",
    "DEPLETABLE_RESOURCES",
    "ALLOCATABLE_RESOURCES",
    "RENEWABLE_RESOURCES",
]
