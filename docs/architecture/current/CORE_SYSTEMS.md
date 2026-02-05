# Core Systems Overview

**Last verified:** 2026-02-05 (Plan #300: added external capabilities system)

This document provides a systematic overview of the core systems that make the simulation work. Each system is critical infrastructure that must be understood before making changes.

**Read this first** when joining the project or investigating issues.

---

## Quick Reference

| # | System | Health | One-Line Purpose |
|---|--------|--------|------------------|
| 1 | [Resource Scarcity](#1-resource-scarcity) | ⚠️ Partial | LLM budgets, rate limits, disk quotas |
| 2 | [Economic Layer](#2-economic-layer-scrip) | ⚠️ Unknown | Scrip currency, transfers, escrow |
| 3 | [Artifact System](#3-artifact-system) | ⚠️ Unknown | Code/data storage, execution, permissions |
| 4 | [Contract System](#4-contract-system) | ⚠️ Unknown | Access control policies |
| 5 | [Agent Lifecycle](#5-agent-lifecycle) | ✓ Working | Loading, thinking, workflows |
| 6 | [Execution Model](#6-execution-model) | ✓ Working | Autonomous loops, timing |
| 7 | [Kernel Interface](#7-kernel-interface) | ⚠️ Unknown | Artifact ↔ world boundary |
| 8 | [Event Logging](#8-event-logging) | ✓ Working | Observability, replay |
| 9 | [External Capabilities](#9-external-capabilities) | ✓ Working | External APIs with human approval |

**Health Legend:**
- ✓ Working - Verified functional
- ⚠️ Partial - Some issues identified
- ⚠️ Unknown - Needs investigation
- ✗ Broken - Known broken

---

## System Details

### 1. Resource Scarcity

**Purpose:** Enforce scarcity of compute resources to drive emergent behavior. Agents must manage limited resources, creating pressure for efficiency and cooperation.

**Health:** ⚠️ Partial - Cost tracking fixed (Plan #281), allocation may be broken (Plan #282)

**Data Flow:**
```
config.yaml (resources.stock.llm_budget.total)
    ↓ distribution: equal
World.__init__() → Ledger.set_resource() for each agent
    ↓
Agent thinks → LLMProvider.generate()
    ↓
LLMProvider.last_usage captures tokens + cost
    ↓
Workflow returns usage (Plan #281)
    ↓
Runner extracts api_cost
    ↓
Ledger.deduct_llm_cost(agent_id, api_cost)
    ↓
Runner skips agents where llm_budget <= 0
```

**Key Files:**
| File | Responsibility |
|------|----------------|
| `config/config.yaml` | `resources.stock.llm_budget`, `rate_limiting` |
| `src/world/ledger.py` | `get_resource()`, `deduct_llm_cost()`, `set_resource()` |
| `src/world/resource_manager.py` | Unified resource operations |
| `src/world/rate_tracker.py` | Rolling window rate limits |
| `src/simulation/runner.py:578,638` | Cost extraction, deduction |

**Config Example:**
```yaml
resources:
  stock:
    llm_budget:
      total: 100.00    # Total $ pool
      unit: dollars
      distribution: equal  # Split among agents
```

**Known Issues:**
- `llm_budget_after: null` in events - see Plan #282

---

### 2. Economic Layer (Scrip)

**Purpose:** Internal currency enabling trade, contracts, and value exchange between agents.

**Health:** ⚠️ Unknown - Needs systematic investigation

**Key Files:**
| File | Responsibility |
|------|----------------|
| `src/world/ledger.py` | `credit_scrip()`, `deduct_scrip()`, `transfer_scrip()` |
| `src/world/mint_auction.py` | Minting via auctions |
| `src/world/mint_tasks.py` | Earning via verifiable tasks |

**Config:**
```yaml
scrip:
  starting_amount: 100  # Each agent starts with 100 scrip
```

**Questions to Investigate:**
- [ ] How does escrow work?
- [ ] What prevents negative balances?
- [ ] How are mint auctions resolved?

---

### 3. Artifact System

**Purpose:** Storage and execution of agent-created code and data.

**Health:** ⚠️ Unknown - Needs systematic investigation

**Key Files:**
| File | Responsibility |
|------|----------------|
| `src/world/artifacts.py` | `ArtifactStore`, metadata, ownership |
| `src/world/executor.py` | Safe code execution, `invoke()` |
| `src/world/action_executor.py` | Action dispatch |
| `src/world/permission_checker.py` | Access control checks |

**Questions to Investigate:**
- [ ] What artifact types exist? (executable, data, working_memory, etc.)
- [ ] How is code sandboxed?
- [ ] What are invoke() semantics?

---

### 4. Contract System

**Purpose:** Access control and policies for artifact interaction.

**Health:** ⚠️ Unknown - Needs systematic investigation

**Key Files:**
| File | Responsibility |
|------|----------------|
| `src/world/contracts.py` | Contract types, permission checking |
| `src/world/kernel_contracts.py` | Built-in: freeware, private |

**Questions to Investigate:**
- [ ] What contract types exist?
- [ ] What's the default when no contract?
- [ ] How do contracts specify permissions?

---

### 5. Agent Lifecycle

**Purpose:** How agents are discovered, loaded, think, and persist state.

**Health:** ✓ Working - Plan #299: Artifact-based agents via genesis loader

**Data Flow (Plan #299):**
```
config/genesis/agents/{name}/
    ├── agent.yaml      (manifest: artifacts + principal)
    ├── strategy.md     (system prompt)
    ├── initial_state.json (initial state)
    └── loop_code.py    (autonomous loop code)
    ↓ genesis loader
World.artifacts gets 3 artifacts:
    - {name}_strategy (text)
    - {name}_state (JSON)
    - {name}_loop (executable, has_loop=True)
    ↓ runner._run_autonomous()
ArtifactLoopManager.discover_loops()
    ↓
ArtifactLoop runs loop_code.py continuously
    ↓
Loop code calls _syscall_llm() for decisions
    ↓
State persisted to {name}_state artifact
```

**Key Files:**
| File | Responsibility |
|------|----------------|
| `src/genesis/loader.py` | Load artifacts from config/genesis/ |
| `src/simulation/artifact_loop.py` | Run has_loop artifacts |
| `src/world/executor.py` | Execute artifact code with _syscall_llm |
| `config/genesis/agents/` | Agent YAML configs |

---

### 6. Execution Model

**Purpose:** How the simulation runs agents in parallel.

**Health:** ✓ Working - Plan #299: ArtifactLoopManager for has_loop artifacts

**Key Files:**
| File | Responsibility |
|------|----------------|
| `src/simulation/runner.py` | SimulationRunner orchestrator |
| `src/simulation/artifact_loop.py` | ArtifactLoopManager for has_loop artifacts |
| `src/simulation/agent_loop.py` | AgentLoopManager (legacy, unused) |
| `src/simulation/pool.py` | Thread pool for parallel execution |
| `src/simulation/supervisor.py` | Crash recovery, backoff |

**Mode:** Autonomous only (Plan #102 removed tick-based mode)

**Plan #299 Change:** Legacy agent loading disabled. ArtifactLoopManager
discovers and runs has_loop=True artifacts from genesis loader.

---

### 7. Kernel Interface

**Purpose:** The sandbox boundary - what artifacts can see and do.

**Health:** ⚠️ Unknown - Needs systematic investigation

**Key Files:**
| File | Responsibility |
|------|----------------|
| `src/world/kernel_interface.py` | `KernelState` (read), `KernelActions` (write) |
| `src/world/kernel_queries.py` | Read-only query types |

**Questions to Investigate:**
- [ ] What can artifacts read via KernelState?
- [ ] What can artifacts do via KernelActions?
- [ ] How is the sandbox enforced?

---

### 8. Event Logging

**Purpose:** Record all state changes for observability and debugging.

**Health:** ✓ Working

**Key Files:**
| File | Responsibility |
|------|----------------|
| `src/world/logger.py` | JSONL event logging |
| `src/simulation/checkpoint.py` | State snapshots |
| `scripts/analyze_run.py` | Log analysis |

**Output:** `logs/run_YYYYMMDD_HHMMSS/events.jsonl`

---

### 9. External Capabilities

**Purpose:** Managed access to external APIs that cost real money.

**Health:** ✓ Working (Plan #300)

**Key Concept:** Unlike internal resources (disk, CPU), external APIs require human approval before agents can use them. This prevents agents from spending real money without consent.

**Request Flow:**
```
Agent discovers need → request_capability()
    ↓
Human reviews event log
    ↓
Human adds config (API key, enabled: true)
    ↓
Agent uses → use_capability()
```

**Key Files:**
| File | Responsibility |
|------|----------------|
| `src/world/capabilities.py` | CapabilityManager, handlers |
| `src/world/kernel_interface.py` | KernelState/KernelActions methods |
| `config/config.yaml` | `external_capabilities` section |

**Built-in Capabilities:**
- `openai_embeddings` - Text embeddings for semantic search
- `anthropic_api` - Direct Anthropic API access

See [capabilities.md](capabilities.md) for full documentation.

---

## Investigation Process

When investigating a system:

1. **Read this section** for overview
2. **Check "Questions to Investigate"** for unknowns
3. **Trace data flow** through listed files
4. **Update this doc** with findings
5. **Create plans** for any issues found

---

## Fail Loud Violations

Systems should fail loudly when invariants are violated. Known patterns to avoid:

```python
# BAD - silent fallback hides bugs
usage = result.get("usage", {"cost": 0.0})

# GOOD - fail loud if missing
usage = result.get("usage")
if usage is None:
    raise RuntimeError("Missing usage data")
```

**Audit needed:** Search codebase for `.get(..., default)` patterns that could hide bugs.

---

## Related Documentation

- `docs/architecture/current/resources.md` - Resource system details
- `docs/architecture/current/execution_model.md` - Execution details
- `docs/architecture/current/agents.md` - Agent details
- `docs/architecture/current/artifacts_executor.md` - Artifact details
- `docs/architecture/current/capabilities.md` - External capabilities (Plan #300)
