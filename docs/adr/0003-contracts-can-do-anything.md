# ADR-0003: Contracts Can Do Anything

**Status:** Accepted
**Date:** 2026-01-11
**Certainty:** 100%

## Context

What capabilities should contracts have when checking permissions?

Original position was "contracts are pure functions" - deterministic, no side effects, no external calls. This was reconsidered.

Arguments for restriction:
- Predictable permission checks
- No cost uncertainty
- Simpler to reason about

Arguments against restriction:
- LLMs are just API calls, like weather APIs
- Agents should choose complexity/cost tradeoff
- System is already non-deterministic via agent behavior

## Decision

**Contracts can do anything. Invoker pays all costs.**

Contracts have full capabilities:
- Call LLM (invoker pays token cost)
- Invoke other artifacts (invoker pays invoke cost)
- Make external API calls (invoker pays)
- Read ledger balances (free)

Contracts still **cannot directly mutate state** - they return decisions, kernel applies changes.

```python
# Contract execution context
namespace = {
    "invoke": lambda *args: invoke_artifact(*args),  # Invoker pays
    "call_llm": lambda *args: call_llm(*args),       # Invoker pays
    "ledger": ReadOnlyLedger(ledger),                # Free reads
}
```

**Cost model is contract-specified:**
```python
{
    "id": "my_contract",
    "cost_model": "invoker_pays",  # or "owner_pays", "split", custom
}
```

Default: invoker pays (sensible for most cases).

## Consequences

### Positive

- **Flexibility** - Contracts can implement any access pattern
- **No artificial limits** - LLM-powered contracts are possible (AI gatekeepers)
- **Emergent complexity** - Agents choose their contract sophistication
- **Uniform model** - No special cases for "what contracts can call"

### Negative

- **Cost uncertainty** - Permission check cost depends on contract complexity
- **Griefing potential** - Malicious contracts could be expensive to check
- **Non-determinism** - Same check may give different results (LLM variance)

### Mitigations

- **Depth limit** (10) prevents infinite loops
- **Timeout** (30s) prevents runaway contracts
- **Invoker pays** means attacker pays for their own attack
- **Sandbox** restricts filesystem/network access

## Related

- Gap #6: Unified Artifact Ontology (contracts are artifacts)
- Gap #14: MCP-Style Artifact Interface
- ADR-0001: Everything is an artifact
- `src/world/contracts.py` - Implementation
- `src/world/genesis_contracts.py` - Genesis contracts
