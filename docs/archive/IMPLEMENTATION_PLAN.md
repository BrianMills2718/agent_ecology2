# Agent Ecology V1 - Implementation Plan

> **Note**: This document is historical reference for completed work.
> Some details (e.g., action costs, gas) have been simplified out.
> See `docs/RESOURCE_MODEL.md` and `CLAUDE.md` for current design.

## Core Ontology: Rights & Reality

This system implements a **physics-first** economic simulation with three distinct value layers:

### Layer 1: Reality (Hard Constraints)
- **User's API Budget**: Total tokens available before "heat death"
- **User's Disk Space**: Total bytes available for artifact storage
- If `Total_System_Spend > USER_BUDGET`, simulation halts

### Layer 2: Rights (Means of Production)
- **Flow Rights (Renewable)**: Compute/token credits per tick (UBI)
  - Resets to `flow_quota` at start of every tick
  - "Use it or lose it"
- **Stock Rights (Fixed)**: Disk space quota per agent
  - Fixed total supply across all agents
  - Cannot write if `used + new > quota`
- Rights are **transferable assets** via `genesis_rights_registry`

### Layer 3: Scrip (Internal Signal)
- Internal currency with no physical utility
- Agents trade Scrip to acquire Layer 2 Rights from each other
- Managed via `genesis_ledger`

---

## The Narrow Waist: Only 3 Physics Verbs

The kernel has exactly **3 actions**:

| Action | Description |
|--------|-------------|
| `read_artifact` | Consume artifact content (costs input tokens) |
| `write_artifact` | Create/update artifact (costs disk quota) |
| `invoke_artifact` | Execute artifact logic (costs gas + price) |

**No kernel `transfer` action.** All transfers via genesis artifacts:
- Scrip: `invoke_artifact("genesis_ledger", "transfer", [from, to, amount])`
- Rights: `invoke_artifact("genesis_rights_registry", "transfer_quota", [from, to, type, amount])`

---

## Genesis Artifacts (System Bootstrap)

### genesis_ledger
Manages Scrip balances.
- `balance(agent_id)` [FREE] - check balance
- `all_balances()` [FREE] - see all balances
- `transfer(from, to, amount)` [1 credit] - transfer scrip

### genesis_rights_registry
Manages Flow/Stock quotas.
- `check_quota(agent_id)` [FREE] - see agent's quotas
- `all_quotas()` [FREE] - see all quotas
- `transfer_quota(from, to, type, amount)` [1 credit] - transfer rights

### genesis_oracle
External value injection via LLM scoring.
- `status()` [FREE] - oracle status
- `submit(artifact_id)` [5 credits] - submit CODE artifact for scoring
- `check(artifact_id)` [FREE] - check submission status
- `process()` [FREE] - score one pending submission

**Oracle Constraint**: Only accepts executable/code artifacts. Rejects text-only content.

### genesis_event_log
Passive observability - agents must READ to learn.
- Public, append-only log of all events (actions, transfers, errors)
- Agents pay real input token costs to read
- No automatic injection into prompts

---

## Completed Implementation

### Phase 1: Real Token Costs ✓
- Token usage captured from LiteLLM (input + output separately)
- Thinking cost = `(input_tokens/1000 * rate_in) + (output_tokens/1000 * rate_out)`
- Agents pay for thinking BEFORE action execution
- Bankrupt agents cannot think (no LLM call until they acquire budget)
- **Context Tax**: Reading artifacts increases future input costs

### Phase 2: Genesis Artifacts ✓
- `genesis_ledger` and `genesis_oracle` as invokable system artifacts
- `invoke_artifact` action type
- System-owned artifacts (cannot be modified)

### Phase 3: Executable Artifacts ✓
- Artifacts with `executable=True`, `price`, and `code` fields
- SafeExecutor using RestrictedPython
- Whitelist: math, json, random, datetime only
- Dual fees: Gas (always paid) + Price (on success only)
- Code must define `run(*args)` function

### Phase 4: Mock Oracle ✓
- LLM evaluates submitted artifacts (0-100 score)
- Mints credits: `score // 10`

---

### Phase 5: Rights & Observability ✓

#### Phase 5a: Remove Kernel Transfer ✓
- Deleted `transfer` action from kernel
- All transfers via `genesis_ledger.transfer()`
- Maintains narrow waist (only read/write/invoke)

#### Phase 5b: Code-Only Oracle ✓
- Oracle rejects non-executable artifacts
- Only code/demos/results accepted
- Agents informed via schema documentation

#### Phase 5c: Passive Event Log ✓
- Created `genesis_event_log` artifact
- All events written here (not injected into prompts)
- Agents must choose to read (paying input token costs)

#### Phase 5d: Rights Registry + Disk Quotas ✓
- Created `genesis_rights_registry`
- Track `flow_quota` (per-tick compute) and `stock_quota` (disk bytes)
- Enforce disk limits on `write_artifact`
- Enable quota transfers between agents

---

### Phase 6: Policies & Controls ✓

#### Phase 6a: Policy Dicts on Artifacts ✓
- Added `policy` field to Artifact class
- `read_price`: Cost to read content (paid to owner)
- `invoke_price`: Cost to invoke (paid to owner)
- `allow_read`, `allow_write`, `allow_invoke`: Access control lists

#### Phase 6b: Hybrid Policy Schema ✓
- Policy allow fields: `Union[List[str], str]`
- Static lists enforced by kernel (fast path): `["*"]`, `["alice", "bob"]`
- Contract references (slow path, V2): `"@dao_voting_contract"`
- Enables future DAOs, voting mechanisms, recursive governance
- V1: Contract references raise `NotImplementedError`

#### Phase 6c: Flow Rights Reset ✓
- Credits now **reset** to `flow_quota` each tick, not accumulate
- "Use it or lose it" - prevents hoarding and rate limit issues
- Agents cannot save credits for burst spending

#### Phase 6d: Remove Free Event Injection ✓
- Agents no longer see events automatically in prompts
- Must invoke `genesis_event_log.read()` to see world events
- Implements passive observability (pay to look)

#### Phase 6e: Budget Pause Check ✓
- Added `budget.max_api_cost` config (in dollars)
- Simulation tracks cumulative API cost
- Pauses gracefully when budget exhausted
- Saves checkpoint to `checkpoint.json` for resumption

---

---

### Phase 7: Code Quality & Infrastructure ✓

| Task | Description | Status |
|------|-------------|--------|
| Package Structure | Proper Python package with relative imports | ✓ |
| Editable Install | `pip install -e .` for development | ✓ |
| mypy Compliance | All 28 source files pass with 0 errors | ✓ |
| Test Suite | 319 tests passing with proper imports | ✓ |
| LLM Log Metadata | Logs include agent_id, run_id, tick | ✓ |
| HTML Dashboard | Real-time visualization with WebSocket | ✓ |
| Oracle Auction | Vickrey auction with UBI distribution | ✓ |

---

### Phase 8: Two-Layer Resource Model ✓

| Task | Description | Status |
|------|-------------|--------|
| Executor Resource Measurement | Track execution time, convert to token cost | ✓ |
| ExecutionResult Schema | Add resources_consumed, execution_time_ms fields | ✓ |
| ActionResult Schema | Add resources_consumed, charged_to fields | ✓ |
| _execute_write Resources | Track disk_bytes consumed | ✓ |
| _execute_invoke Resources | Track llm_tokens for genesis methods | ✓ |
| resource_policy Enforcement | caller_pays vs owner_pays for executables | ✓ |
| Resource Tracking Tests | 14 tests for resource logic | ✓ |
| SimulationEngine Tests | 36 tests for physics calculations | ✓ |
| Agent Event Display | 5 event types (action, tick, intent_rejected, oracle_auction, thinking_failed) | ✓ |
| SimulationEngine | Physics calculations extracted to dedicated class | ✓ |
| SimulationRunner Integration | Engine used for rates, budget tracking, exhaustion checks | ✓ |

**Key Implementation:**
- `_time_to_tokens()`: Converts execution time to token cost (configurable rate)
- Scrip and resources deducted independently (two-layer separation)
- Owner can subsidize resources via `resource_policy: "owner_pays"`
- Different error messages for caller vs owner insufficient resources

---

## Future Work

> **See [architecture/GAPS.md](architecture/GAPS.md)** for the current list of implementation gaps and their priorities.
> **See [plans/README.md](plans/README.md)** for implementation plans for each gap.

Key gaps being tracked:
- **#1 Token Bucket**: Rolling window resource accumulation
- **#2 Continuous Execution**: Autonomous agent loops (major refactor)
- **#6 Unified Artifact Ontology**: Everything is an artifact (agents, contracts, data)
- **#16 genesis_store**: Artifact discovery mechanism
- **#20 Migration Strategy**: Phased transition from current to target architecture

---

## Configuration

```yaml
world:
  max_ticks: 100

rights:
  default_flow_quota: 50      # Credits per tick (resets, not accumulates)
  default_stock_quota: 10000  # Bytes per agent

costs:
  read_artifact: 2           # Base cost (real cost = input tokens)
  write_artifact: 5          # Scrip cost (real cost = bytes used)
  invoke_artifact: 1         # Base cost
  execution_gas: 2           # Gas for executable artifacts

  credits_per_1k_input_tokens: 1
  credits_per_1k_output_tokens: 3

budget:
  max_api_cost: 1.00         # Max API cost in dollars (0 = unlimited)
  checkpoint_file: "checkpoint.json"  # State saved here on pause
```

---

## Action Schema (Agent Reference)

```
1. read_artifact - Read artifact content
   {"action_type": "read_artifact", "artifact_id": "<id>"}
   Cost: 2 credits + future input token cost

2. write_artifact - Create/update artifact
   Regular: {"action_type": "write_artifact", "artifact_id": "<id>",
             "artifact_type": "<type>", "content": "<content>"}

   Executable: {"action_type": "write_artifact", "artifact_id": "<id>",
                "artifact_type": "executable", "content": "<description>",
                "executable": true, "price": <credits>, "code": "<python>",
                "resource_policy": "caller_pays"|"owner_pays"}
   Cost: 5 credits + disk quota consumed

3. invoke_artifact - Call artifact method
   {"action_type": "invoke_artifact", "artifact_id": "<id>",
    "method": "<method>", "args": [...]}
   Cost: 1 credit + method cost + gas (if executable)

Genesis Methods:
- genesis_ledger.balance([agent_id]) [FREE]
- genesis_ledger.transfer([from, to, amount]) [1 credit]
- genesis_rights_registry.check_quota([agent_id]) [FREE]
- genesis_rights_registry.transfer_quota([from, to, type, amount]) [1 credit]
- genesis_oracle.submit([artifact_id]) [5 credits] - CODE ONLY
- genesis_oracle.process([]) [FREE]
- genesis_event_log.read([offset, limit]) [FREE] - pays input tokens
```

---

## Design Principles

1. **Physics First**: Real API costs, real disk limits
2. **Narrow Waist**: Only 3 verbs, everything else via invoke
3. **Passive Observability**: Agents pay to read, nothing injected
4. **Rights vs Scrip**: Separate means-of-production from currency
5. **Code Creates Value**: Oracle only rewards executable artifacts
