"""Resource type constants (TD-004).

Canonical names for all resource types used in the simulation.
Use these constants instead of string literals to prevent typos
and enable IDE navigation.

Resource Categories:
- DEPLETABLE: Once spent, gone forever (e.g., llm_budget in dollars)
- ALLOCATABLE: Quota that can be used and reclaimed (e.g., disk bytes)
- RENEWABLE: Rate-limited, replenishes over time (e.g., llm_tokens per minute)
"""

# === Depletable Resources (stock, finite) ===
# Once spent, these are gone - scarcity drives behavior

RESOURCE_LLM_BUDGET = "llm_budget"
"""LLM budget in dollars. Primary constraint for LLM usage (Plan #153)."""

# === Allocatable Resources (quota, reclaimable) ===
# Agents have a quota; usage can be reclaimed (e.g., deleting artifacts)

RESOURCE_DISK = "disk"
"""Disk storage in bytes. Artifacts consume disk; deletion reclaims it."""

# === Renewable Resources (rate-limited) ===
# Replenishes over time via token bucket / rolling windows

RESOURCE_LLM_TOKENS = "llm_tokens"
"""LLM tokens (rate-limited). DEPRECATED: Use llm_budget for cost constraint."""

RESOURCE_CPU = "cpu_seconds"
"""CPU time in seconds per period."""

# === Legacy / Deprecated ===
# Kept for backward compatibility - prefer canonical names above

RESOURCE_COMPUTE = "compute"
"""DEPRECATED: Old name for llm_tokens. Use RESOURCE_LLM_TOKENS instead."""

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
    # Deprecated
    "RESOURCE_COMPUTE",
    # Collections
    "ALL_RESOURCES",
    "DEPLETABLE_RESOURCES",
    "ALLOCATABLE_RESOURCES",
    "RENEWABLE_RESOURCES",
]
