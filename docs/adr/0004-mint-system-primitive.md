# ADR-0004: Mint as System Primitive and System/Genesis Distinction

**Status:** Accepted
**Date:** 2026-01-12
**Certainty:** 95%

## Context

The architecture conflated two distinct layers:

1. **System primitives** - Hardcoded state and capabilities that agents cannot replace
2. **Genesis artifacts** - Pre-seeded interfaces to system state that solve cold-start

The "oracle" was categorized as a genesis artifact, implying agents could theoretically replace it. But minting (creating new scrip) is a privileged operation that must be developer-controlled. If agents could create or modify minters, they would game the money supply.

Additionally, "oracle" is confusing terminology—it suggests "reveals truth" when the actual function is creating new currency based on external validation.

## Decision

### 1. Rename oracle → mint

The component that creates new scrip is now called the **mint**. This accurately describes its function: creating currency.

- `genesis_oracle` → `genesis_mint` (the interface)
- Oracle scoring → Mint scoring
- Oracle auction → Mint auction

### 2. Mint is a system primitive

The **minting capability** is system-level, not genesis-level:

- Agents cannot create minters
- Agents cannot modify minting rules (scoring, amounts, timing)
- The developer configures minting rules
- `genesis_mint` is just an interface for agents to submit artifacts for scoring

### 3. Clarify system vs genesis distinction

**System Primitives (the "Physics")** - State stores and capabilities hardcoded in Python:

| Primitive | Type | Description |
|-----------|------|-------------|
| Ledger | State | Scrip and resource balances |
| Artifact store | State | All artifacts and metadata |
| Event log | State | Immutable audit trail |
| Rights registry | State | Resource quotas per principal |
| Mint | Capability | Creates new scrip (developer-configured rules) |
| Execution engine | Capability | Runs agent loops, action dispatch |
| Rate tracker | Capability | Enforces rolling window limits |

**Genesis Artifacts (Cold-Start Infrastructure)** - Interfaces to system primitives:

| Artifact | Interfaces To |
|----------|---------------|
| `genesis_ledger` | Ledger state |
| `genesis_mint` | Mint capability |
| `genesis_escrow` | Artifact store (trading logic) |
| `genesis_rights_registry` | Rights registry |
| `genesis_store` | Artifact store (discovery) |
| `genesis_event_log` | Event log |

Genesis artifacts could theoretically be replaced with alternative interfaces. The underlying system state they access cannot.

### 4. State should be DB-backed

System state (Ledger, Artifact store, Event log, Rights registry) should be persisted to SQLite with WAL for crash safety, not just in-memory with checkpoints.

## Consequences

### Positive

- **Clearer terminology** - "Mint" accurately describes currency creation
- **Correct security model** - Minting is properly protected as system-level
- **Better architecture understanding** - Clear separation of state vs interfaces
- **Crash safety** - DB-backed state with proper durability guarantees

### Negative

- **Terminology migration** - 34+ files reference "oracle"
- **Code changes** - Refactoring oracle → mint in implementation
- **DB complexity** - Adding SQLite dependency and migration logic

### Neutral

- Genesis artifacts remain the primary interface for agents
- Agents still submit artifacts for scoring via `genesis_mint`
- External validation sources unchanged

## Related

- ADR-0001: Everything is an Artifact (clarifies what genesis artifacts are)
- Gap #34: Oracle → Mint Rename (code refactoring)
