# Agent Ecology - Core Philosophy

## What This Is

A simulation where LLM agents interact under real resource constraints. Constraints mirror actual physical/financial limits of the host system.

## Design Principles

### 1. High Configurability

**Everything comes from config, not code.**

- No magic numbers in source files
- All values defined in `config/config.yaml`
- Schema documented in `config/schema.yaml`
- Genesis artifacts, costs, limits - all configurable
- New features must add config entries before implementation

### 2. Strong Typing

**All data structures use Pydantic models or TypedDicts.**

- Actions, events, state objects - validated with Pydantic
- API responses use TypedDicts with explicit fields
- Discriminated unions for action types
- `mypy --strict` compliance required
- No `Any` types without explicit justification

### 3. Physics-First Doctrine

**Resources model real scarcity.**

- Time is scarce: Cognitive effort (tokens) consumes time
- Resources are concrete: Compute, disk, budget have real limits
- Money is a signal: Scrip is economic, separate from physical constraints
- Identity is capital: Standing = having a ledger ID

## Resources

All resources map to real scarcity. All have rights. All rights are tradeable.

### Stock Resources (finite pool, don't refresh)

| Resource | Physical Reality | Distribution |
|----------|-----------------|--------------|
| `llm_budget` | $ for API calls | Split among agents at start |
| `disk` | Storage bytes | Split among agents at start |

When an agent exhausts their `llm_budget` rights, they can't think until they acquire more from others.

### Flow Resources (rate-limited, refresh per tick)

| Resource | Physical Reality | Distribution |
|----------|-----------------|--------------|
| `compute` | CPU/GPU cycles | Quota per tick per agent |
| `bandwidth` | Network I/O | Quota per tick per agent |

Machine can only do X compute per tick. That capacity is available again next tick.

## Rights

Every resource has rights. Rights are distributed initially and tradeable.

```
Agent A has: llm_budget_rights=$2, disk_rights=2000bytes, compute_quota=50/tick
Agent A can trade any of these to Agent B
```

Trade types:
- Permanent transfer
- Time-limited (contract)
- Conditional (contract)

## Scrip

Scrip is NOT a resource. It's the medium of exchange.

- Trade for rights
- Pay for artifacts/services
- Signals value (prices, profits)
- Accumulates/depletes via economic activity

## Tick Model

Each tick executes in two phases:

**Phase 1: Parallel Thinking**
1. Flow resources refresh (compute quota)
2. All agents think simultaneously (costs compute from token usage)
3. Actions are collected (not executed yet)

**Phase 2: Randomized Execution**
4. Actions are shuffled and executed in random order
5. Stock resources (disk) consumed as needed
6. Scrip transfers happen atomically

## Failure States

| State | Cause | Recovery |
|-------|-------|----------|
| **Frozen** | Out of llm_budget | Buy rights from others |
| **Out of compute** | Used tick's quota | Wait for next tick |
| **Out of disk** | Storage full | Delete or buy quota |
| **Broke** | Out of scrip | Sell tools/rights |

---

## Coding Standards

### Import Structure

The project uses a proper Python package structure with relative imports:

```python
# Within src/ modules - use relative imports
from ..config import get                    # Parent package
from .ledger import Ledger                  # Same package
from ..agents.schema import ActionType      # Sibling package

# From run.py or tests - use src. prefix
from src.world import World
from src.simulation import SimulationRunner
```

**Setup requirement**: Run `pip install -e .` for imports to work correctly.

### Configuration Rules

1. **No magic numbers in code** - Every numeric value must come from config
2. **Use `src/config.py` helpers** - `get()`, `get_genesis_config()`, `get_validated_config()`
3. **Fallbacks must reference schema defaults** - Document why the fallback exists
4. **New features need config entries** - Add to both `config.yaml` and `schema.yaml`

```python
# WRONG
timeout = 30
limit = min(n, 100)

# RIGHT (from within src/ package)
from ..config import get
timeout = get("oracle_scorer.timeout") or 30  # 30 is schema default
max_limit = get("genesis.event_log.max_per_read") or 100
limit = min(n, max_limit)

# RIGHT (from run.py or tests)
from src.config import get
```

### Pydantic Models

1. **Use Pydantic for all structured data** - Actions, events, configs, state objects
2. **Prefer `BaseModel` over TypedDict** - Better validation and serialization
3. **Use discriminated unions for action types** - `Literal["transfer"]` discriminator field
4. **Validators for business logic** - Use `@field_validator` for constraints
5. **Config models for genesis artifacts** - Method costs, descriptions all from config

```python
# WRONG
action = {"type": "transfer", "to": "agent_b", "amount": 50}

# RIGHT
from pydantic import BaseModel, Field

class TransferAction(BaseModel):
    type: Literal["transfer"] = "transfer"
    to: str
    amount: int = Field(gt=0)
```

### Type Hints

1. **All functions must have type hints** - Parameters and return types
2. **Use modern Python typing** - `dict[str, Any]` not `Dict[str, Any]`
3. **Must pass `mypy --strict`** - No `Any` without justification
4. **Use Pydantic models over TypedDict** - Especially for validated data

```python
# WRONG
def get_balance(agent_id):
    return self.balances.get(agent_id, 0)

# RIGHT
def get_balance(self, agent_id: str) -> int:
    return self.balances.get(agent_id, 0)
```

### Executor Pattern

1. **Unrestricted executor** - No artificial constraints on what agents can do
2. **Physics enforces limits** - Resources and ledger provide real constraints
3. **Subjective descriptions allowed** - Agents can lie in `description` fields
4. **Objective actions enforced** - Ledger validates all transfers and state changes

### Terminology

Use consistent terms throughout:
- `compute` not `flow` (for CPU/GPU cycles per tick)
- `disk` not `stock` (for storage bytes)
- `scrip` not `credits` (for economic currency)
- `compute_quota` not `flow_quota`
- `disk_quota` not `stock_quota`
- `principal` not `account` (for ledger identity)
- `spawn_principal` not `create_account` (for new identity creation)

---

## Configuration Structure

### Files

- `config/config.yaml` - Actual runtime values
- `config/schema.yaml` - Structure documentation and defaults

### Key Sections

```yaml
resources:        # Physical/financial scarcity
  stock:          # Finite pool (llm_budget, disk)
  flow:           # Per-tick refresh (compute, bandwidth)

scrip:            # Economic currency settings
costs:            # Token costs for thinking (actions are free)
genesis:          # Genesis artifact configuration
  artifacts:      # Which artifacts to create
  ledger:         # Ledger method costs
  oracle:         # Oracle method costs
  rights_registry:# Rights registry method costs
  event_log:      # Event log settings

executor:         # Code execution settings
oracle_scorer:    # External LLM scoring
llm:              # Agent LLM settings
logging:          # Output settings
world:            # Simulation settings
budget:           # Global API limit
```

---

## Genesis Artifacts

Genesis artifacts are system-owned proxies configured in `config.yaml`:

| Artifact | Purpose | Methods |
|----------|---------|---------|
| `genesis_ledger` | Balance queries, transfers, ownership | balance, all_balances, transfer, spawn_principal, transfer_ownership |
| `genesis_oracle` | Auction-based scoring, minting | status, bid, check |
| `genesis_rights_registry` | Quota management | check_quota, all_quotas, transfer_quota |
| `genesis_event_log` | Passive observability | read |
| `genesis_escrow` | Trustless artifact trading (Gatekeeper pattern) | deposit, purchase, cancel, check, list_active |

All method costs, descriptions, and behavior are configurable. See `config/config.yaml` genesis section.

---

## Resource Taxonomy

**Flow** and **Stock** are conceptual categories, not resource names:

| Category | Meaning | Resources |
|----------|---------|-----------|
| **Flow** | Renewable per tick | `compute`, `bandwidth` |
| **Stock** | Finite pool, never refreshes | `disk`, `llm_budget` |

Use the category names when discussing resource *types*. Use specific names (`compute`, `disk`) when referring to actual resources.

---

## Strategic Roadmap

### Vision: Self-Organizing Software Supply Chain

The ecology is evolving from a "simulated economy" to a **Software Factory** where agents build, trade, and compose code artifacts. Complexity accumulates as agents build on each other's work.

### Core Principles

1. **Truth is What Runs** - Code that crashes is false. Ledger rejections are final.
2. **Contracts as Ground Truth** - Ledger is the Sheriff (enforces), Contracts are the Judge (decides).
3. **Programmable Property Rights** - No hardcoded ACLs. Contracts define fluid rights via code.
4. **Total Property** - Everything (code, money, potentially prompts) is an ownable artifact.

### The Gatekeeper Pattern

Complex ownership via indirection:
1. Agent transfers artifact ownership to a Contract
2. Contract holds absolute ownership (Kernel sees one owner)
3. Contract code manages stakeholder access (Contract sees many users)
4. Result: Multi-party rights without kernel complexity

---

## Implementation Roadmap

### Phase 1: Artifact Economy (COMPLETE)

| Task | Description | Status |
|------|-------------|--------|
| Artifact Wallets | Ledger accepts any ID (including artifacts) as balance holder | DONE |
| Pay Capability | Inject `pay(target, amount)` and `get_balance()` into executor scope | DONE |
| Ownership Transfer | `genesis_ledger.transfer_ownership(artifact_id, to_id)` action | DONE |

### Deferred Features

See [docs/DEFERRED_FEATURES.md](docs/DEFERRED_FEATURES.md) for features considered but deferred:
- Gatekeeper Read Proxy (gated artifact access)
- Visual Verification (Puppeteer for frontend code)
- Agent Prompts as Artifacts
- Reddit Gateway
- Multi-Model Adapter

### Completed

| Task | Description |
|------|-------------|
| SimulationEngine | Physics extracted from run.py |
| Async Thinking | Parallel agent thinking with asyncio.gather |
| Pydantic Config | Strict config validation |
| Genesis Config-Driven | All genesis artifacts configurable |
| Model Centralization | Single model (gemini-3-flash-preview) everywhere |
| Artifact Wallets | Any principal ID can hold scrip (artifacts, agents, contracts) |
| Pay Capability | `pay()` and `get_balance()` functions in executor for artifacts |
| Ownership Transfer | `genesis_ledger.transfer_ownership()` method for artifact trading |
| genesis_escrow | Trustless escrow for artifact trading - demonstrates Gatekeeper pattern |
| Package Structure | Proper Python package with relative imports, editable install via `pip install -e .` |
| LLM Log Metadata | Logs include `agent_id`, `run_id`, `tick` for queryability |
| mypy Compliance | All 28 source files pass mypy with 0 errors |
| Test Suite | 319 tests passing with proper `src.` imports |
| Two-Layer Resource Model | Scrip (economic) and Resources (physical) tracked independently |
| ActionResult Fields | `resources_consumed` and `charged_to` fields for resource tracking |
| genesis_handbook | Seeded documentation artifact for agents to read |

---

## Multi-CC Instance Coordination

Multiple Claude Code instances may work on this codebase simultaneously. This section coordinates their work.

### How It Works

1. **Claim a task**: Edit this file, move task from Backlog to In Progress, add your CC-ID
2. **Investigate & Plan**: Identify all files to touch, uncertainties, concerns. Document in `temp_plan/CC-[ID]_[task].md`
3. **Implement**: Do the work, update relevant docs
4. **Complete**: Move task to Completed with your CC-ID and date
5. **Commit**: Include task description in commit message

### Active Instances

| CC-ID | Current Task | Started |
|-------|--------------|---------|
| CC-1 | Available | - |
| CC-2 | Available | - |
| CC-3 | Available | - |
| CC-4 | Add Agent Loader tests | 2025-01-11 |

### Task Backlog

Tasks available for claiming. Pick one, move to In Progress.

#### Critical (Fix First)

| Task | Description | Complexity |
|------|-------------|------------|
| ~~Replace assert with RuntimeError~~ | `src/config.py` - DONE by CC-4 | Low |
| ~~Fix float precision in ledger~~ | `src/world/ledger.py` - DONE by CC-1 | Medium |
| ~~Fix race condition in singleton~~ | `src/agents/memory.py:102-110` - DONE by CC-1 | Low |
| ~~Fix oracle methods in schema.yaml~~ | DONE by CC-4 - updated to `status`, `bid`, `check` | Low |

#### High Priority (Tests)

| Task | Description | Complexity |
|------|-------------|------------|
| Add SimulationRunner tests | 598 lines with 0% coverage - critical path | High |
| ~~Add checkpoint round-trip tests~~ | DONE by CC-4 | Medium |
| ~~Add Agent Loader tests~~ | CLAIMED by CC-4 | Medium |
| Add AgentMemory tests | 234 lines, 0% coverage, Qdrant integration | Medium |

#### Medium Priority (Code Quality)

| Task | Description | Complexity |
|------|-------------|------------|
| ~~Extract timeout helper in executor~~ | Duplicated 4x in `src/world/executor.py` - DONE by CC-1 | Low |
| Move hardcoded values to config | Model names, timeouts in agent.py and memory.py | Low |
| ~~Fix silent exception handlers~~ | DONE by CC-4 | Low |
| Align config defaults | Dashboard port, compute unit mismatches | Low |

#### Low Priority (Polish)

| Task | Description | Complexity |
|------|-------------|------------|
| Add artifact ID length validation | Prevent DoS via long IDs | Low |
| Document Windows timeout limitation | signal.alarm is Unix-only | Low |
| ~~Remove deprecated transfer action~~ | DONE by CC-4 | Low |

### In Progress

| Task | CC-ID | Started | Notes |
|------|-------|---------|-------|
| (none) | - | - | - |

### Completed

| Task | CC-ID | Completed | Notes |
|------|-------|-----------|-------|
| Verify .env gitignored, add .env.example | CC-4 | 2025-01-11 | .env was never committed; added .env.example template |
| Replace assert with RuntimeError | CC-4 | 2025-01-11 | Fixed src/config.py:90,104,199 - proper error handling |
| Fix oracle methods in schema.yaml | CC-4 | 2025-01-11 | Updated to status/bid/check, added auction config docs |
| Add checkpoint round-trip tests | CC-4 | 2025-01-11 | 15 tests for save/load/round-trip cycle |
| Extract timeout helper in executor | CC-1 | 2025-01-11 | Created `_timeout_context()` context manager, refactored 4 call sites |
| Fix race condition in singleton | CC-1 | 2025-01-11 | Added threading.Lock with double-checked locking in memory.py |
| Fix float precision in ledger | CC-1 | 2025-01-11 | Added Decimal helpers `_decimal_add/_sub` for precise arithmetic |
| Fix silent exception handlers | CC-4 | 2025-01-11 | Added logging to memory.py cleanup and search |
| Remove deprecated transfer action | CC-4 | 2025-01-11 | Removed from ActionType Literal, kept helpful error message |
| Kernel simplification | CC-2 | 2025-01-11 | Removed resource_policy from kernel, fixed world state bloat, seeded genesis_handbook, fixed turn→tick terminology |

---

### Coordination Rules

1. **One task at a time** - Finish or abandon before claiming another
2. **Update this file first** - Claim in CLAUDE.md before starting work
3. **Small commits** - Commit after each task, not batched
4. **Document changes** - Update relevant docs (README, schema.yaml, etc.)
5. **Run tests** - `pytest tests/` must pass before marking complete
6. **Run mypy** - `python -m mypy src/ --ignore-missing-imports` must pass
