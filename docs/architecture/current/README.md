# Current Architecture

Documentation of how the system works TODAY. Updated as code changes.

Last verified: 2026-01-15

---

## Overview

The Agent Ecology is a multi-agent system where LLM-powered agents observe shared world state, propose actions, and execute them within resource constraints.

**Default: Autonomous Execution** (`use_autonomous_loops: true`)
- Agents run independently via `AgentLoop`
- Resource-gated by `RateTracker` (rolling window rate limiting)
- No tick synchronization required

**Legacy: Tick-Synchronized Mode** (`--ticks N` CLI flag)
- Two-phase commit: Observe (parallel) → Execute (sequential randomized)
- Useful for debugging/deterministic replay

**Key Constraints:**
- **Strict resource limits** - No debt, cannot spend more than available
- **Rate-limited execution** - RateTracker enforces rolling window limits

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

### Execution Flow

**Autonomous Mode (Default):**
```
1. Each agent runs in independent AgentLoop
2. RateTracker gates resource consumption (rolling window)
3. Agent calls LLM, proposes action
4. World executes action
5. Agent sleeps, repeats
```

**Tick Mode (Legacy, `--ticks N`):**
```
1. advance_tick() - increment tick counter
2. mint.on_tick() - resolve auctions if any
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
| Renewable | llm_tokens | RateTracker | Rolling window rate limit |
| Depletable | llm_budget | SimulationEngine | Per-agent $ budget (Plan #12) |
| Allocatable | disk | ArtifactStore | Quota-based, reclaimable |
| Currency | scrip | Ledger | Persistent, transfers only |

**Note:** Legacy config uses "compute" which maps to "llm_tokens".

### Key Constraints
- No negative balances (resources or scrip)
- Cannot spend more than available
- Rate limits enforced via RateTracker (wait for capacity)
