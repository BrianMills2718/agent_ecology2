# Current Architecture

Documentation of how the system works TODAY. Updated as code changes.

Last verified: 2026-01-12

---

## Overview

The Agent Ecology is a tick-synchronized multi-agent system where LLM-powered agents observe shared world state, propose actions, and execute them within resource constraints.

**Key Characteristics:**
- **Tick-synchronized execution** - All agents act within discrete tick cycles
- **Two-phase commit** - Observe (parallel) → Execute (sequential randomized)
- **Strict resource constraints** - No debt, cannot spend more than available
- **Discrete flow refresh** - Flow resources reset each tick (use-or-lose)

---

## Documents

| Document | Description |
|----------|-------------|
| [running.md](running.md) | How to run and observe simulations |
| [execution_model.md](execution_model.md) | Tick loop, two-phase commit, timing |
| [agents.md](agents.md) | Agent lifecycle, thinking, memory |
| [resources.md](resources.md) | Flow/stock resources, scrip, costs |
| [genesis_artifacts.md](genesis_artifacts.md) | System services (ledger, oracle, etc.) |
| [artifacts_executor.md](artifacts_executor.md) | Artifact storage, policies, code execution |
| [configuration.md](configuration.md) | Config loading, validation, Pydantic schema |
| [supporting_systems.md](supporting_systems.md) | Checkpoint, logging, dashboard |
| [ci.md](ci.md) | GitHub Actions CI (pytest, mypy) |

---

## Quick Reference

### Execution Flow (Per Tick)
```
1. advance_tick() - increment, reset flow resources
2. oracle.on_tick() - resolve auctions if any
3. get_state_summary() - snapshot world state
4. PHASE 1: All agents think in parallel (asyncio.gather)
5. PHASE 2: Execute actions in randomized order
6. Optional: checkpoint save
7. Sleep for rate_limit_delay
8. Repeat
```

### Resource Types
| Type | Examples | Tracked By | Behavior |
|------|----------|------------|----------|
| Flow | llm_tokens | Ledger | Reset each tick to quota |
| Stock | disk | ArtifactStore | Quota-based, cumulative usage |
| Stock | llm_budget | SimulationEngine | Global API budget (not per-agent) |
| Currency | scrip | Ledger | Persistent, transfers only |

**Note:** Config uses "compute" as the flow resource name, internally stored as "llm_tokens".

### Key Constraints
- No negative balances (resources or scrip)
- Cannot spend more than available
- Flow resources lost if unused at tick end
