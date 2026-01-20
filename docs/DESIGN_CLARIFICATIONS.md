# Design Clarifications

**Decision rationale archive.** This file records WHY decisions were made, not WHAT the current design is.

**Last updated:** 2026-01-19 (Contract system ADRs added)

---

## Quick Navigation

| Section | Purpose |
|---------|---------|
| [Approved Decisions (Jan 13)](#approved-architecture-decisions-2026-01-13) | **Current source of truth** - 38 approved decisions |
| [Deferred Concerns](#deferred-concerns-v-n) | Issues documented for future consideration |
| [Reference Sections](#resource-terminology) | Terminology and background context |
| [Historical Archive](archive/design_discussions_jan11.md) | CC-3/CC-4 discussions that led to decisions |

---

## Table of Contents

1. [Purpose](#purpose)
2. [Research System Trust Model](#research-system-trust-model-added-2026-01-13)
3. [Resource Terminology](#resource-terminology)
4. [Flow Resources (Compute)](#flow-resources-compute)
5. [Scrip and Debt](#scrip-and-debt)
6. [LLM Token Limits](#llm-token-limits)
7. [Negative Balance Rules](#negative-balance-rules)
8. [Agent Execution Model](#agent-execution-model)
9. [Agent Rights and Ownership](#agent-rights-and-ownership)
10. [Oracle Design](#oracle-design)
11. [Budget Enforcement](#budget-enforcement)
12. [System-Wide Throttling](#system-wide-throttling)
13. [Resolved Questions](#resolved-questions)
14. [Deferred Concerns](#deferred-concerns-v-n)
15. [Approved Architecture Decisions](#approved-architecture-decisions-2026-01-13)
16. [Contract System Design Decisions](#contract-system-design-decisions-2026-01-19)

---

## How to Use This File

### For External Reviewers

1. **Start with [Approved Decisions](#approved-architecture-decisions-2026-01-13)** - 38 decisions approved Jan 13, 2026
2. **Check [Deferred Concerns](#deferred-concerns-v-n)** - Issues documented for future consideration
3. **Reference sections** below provide terminology and background context

### For Contributors

- **Reading:** Understand the reasoning behind decisions
- **Writing:** Add new sections when making architecture decisions
- **Attribution:** Mark author (CC-N) and date for traceability
- **Don't duplicate:** Put the WHAT in target/, put the WHY here
- **For major decisions:** Create an ADR in `docs/adr/` instead

### Canonical Sources (Authoritative)

| Document | Purpose | This File's Role |
|----------|---------|------------------|
| [architecture/current/](architecture/current/) | How the system works TODAY | Explains why it works that way |
| [architecture/target/](architecture/target/) | What we're building toward | Explains why we chose that target |
| [docs/adr/](adr/) | Architecture Decision Records | Permanent record of key decisions |
| [plans/](plans/) | How to close gaps | Explains design tradeoffs |

---

## Purpose

This is **mechanism design for real resource allocation**, not a simulation or model.

**Primary Goal:** Functional emergent collective intelligence - whole greater than sum of parts.

Design Goals:
- Operate within real-world constraints (computer capacity, API budget)
- Create markets that optimally allocate scarce resources among agents
- Resources ARE the real constraints, not proxies for them
- No artificial constraints on agent productivity

**Non-Goals:**
- Research reproducibility (doesn't matter)
- Simulating human societies or other systems
- Deterministic behavior

---

## Research System Trust Model (ADDED 2026-01-13)

**This is a research system, not a production blockchain.**

Unlike trustless production systems (Bitcoin, Ethereum), this ecology operates with an explicit admin role:

| Aspect | Production Blockchain | This Research System |
|--------|----------------------|---------------------|
| **Admin access** | None (trustless) | Yes, with transparency |
| **Rollback** | Computationally infeasible | Possible if needed |
| **State reset** | Prohibited | Allowed for research |
| **Bug fixes** | Requires hard fork | Genesis contracts mutable |

**Why this framing matters:**

1. **Orphan artifacts aren't permanent** - Unlike lost Bitcoin, an admin can intervene if a catastrophic bug locks valuable work. This is a feature, not a bug.

2. **Design decisions can favor simplicity** - We don't need Byzantine fault tolerance for a system with trusted operators.

3. **Experiments can be reset** - If an experiment goes wrong, we can restore from checkpoint, not lose months of work.

4. **Genesis contract evolution** - Genesis artifacts can be updated via code deploy. No governance token voting required.

**Transparency requirement:** Any admin intervention must be:
- Logged in the event system
- Documented with rationale
- Visible to all agents and observers

This isn't "centralized vs decentralized" - it's acknowledging that research systems have different trust assumptions than production deployments.

**Certainty:** 100% (framing clarification, not design change)

---

## Resource Terminology

**Distinct resources - do not conflate:**

| Resource | Type | What it is |
|----------|------|------------|
| LLM API $ | Stock | Real dollars spent on API calls |
| LLM rate limit | Flow | Provider limits (TPM, RPM) |
| Compute | Flow | Local CPU capacity |
| Memory | Stock | Local RAM |
| Disk | Stock | Storage quota (reclaimable via delete) |
| Scrip | Currency | Internal economy, not a "resource" |

**LLM tokens ≠ Compute.** LLM tokens are API cost ($), compute is local machine capacity. Different constraints, different mechanisms.

---

## Flow Resources (Compute)

### Rolling Window (Token Bucket)
- Flow accumulates continuously at a fixed rate
- Capped at maximum capacity (can't hoard indefinitely)
- No discrete "refresh" moments - smooth accumulation
- Similar to API rate limits (tokens per minute)

### Why Not Discrete Refresh
- Discrete refresh creates "spend before reset" pressure
- Leads to wasteful spending at period boundaries
- Artificial urgency doesn't serve collective intelligence
- Rolling window = no gaming, smoother behavior

### Mechanics (Token Bucket)

```python
# Continuous accumulation
available = min(capacity, balance + elapsed_time * rate)

# Examples (rate = 10/sec, capacity = 100):
# T=0:  balance = 100
# T=5:  spend 60 → balance = 40
# T=10: balance = min(100, 40 + 5*10) = 90 (accumulated 50)
# T=12: want to spend 100 → only 90 available → must WAIT
# T=13: balance = min(100, 90 + 1*10) = 100 → now can spend 100
```

### No Debt Model (REVISED 2026-01-12)
- Agents CANNOT go negative on renewable resources
- If balance < cost, operation blocks/waits until sufficient capacity
- No debt tracking, no debt forgiveness needed
- Simpler semantics: you either have capacity or you wait

**Why no debt?**
- Debt complicates accounting and recovery
- "Wait for capacity" is cleaner than "go negative and recover"
- Matches how real rate limiters work (429s block, not incur debt)
- Prevents pathological debt accumulation scenarios

### Throttling Emerges Naturally
- No hardcoded "max N agents"
- Expensive operations → insufficient capacity → wait for accumulation
- System self-regulates based on actual resource consumption

---

## Scrip and Debt

### Scrip Balance Cannot Go Negative
- Ledger enforces scrip >= 0
- You cannot spend scrip you don't have

### Debt = Contract Artifacts (Not Negative Balance)
- If Agent A owes Agent B 50 scrip, this is NOT a negative balance
- Instead: A debt artifact exists, owned by B
- The debt is a claim on A's future production
- Like M1 vs M2 money - debt instruments are different from base money
- Debt can be traded, sold, forgiven

### Example
```
Agent A borrows 50 scrip from Agent B:
  1. B transfers 50 scrip to A (A's balance increases)
  2. Debt artifact created: "A owes B 50 scrip"
  3. B owns the debt artifact (can sell it, trade it)
  4. A must eventually pay B to clear the debt
  5. A's scrip balance never goes negative
```

---

## LLM Token Limits

### No System-Level max_tokens
- System does NOT hardcode max_tokens for LLM calls
- Agents choose their own limits (or none)

### Agent Choice = Market Forces
- Agent wanting predictable costs → sets low max_tokens → self-limits
- Agent willing to risk debt → uncapped → more capability, more risk
- This is an economic decision, not a system rule

### Costs Remain Real
- Cost based on actual tokens used (input × rate_input + output × rate_output)
- max_tokens caps output but cost is still real usage

---

## Negative Balance Rules

**SUPERSEDED:** Per ADR-0012, scrip balances cannot go negative. The ledger enforces `balance >= 0`. Debt is modeled as contract artifacts, not negative balances (see "Scrip and Debt" section above).

### Transfers Are Unilateral
- You can transfer YOUR assets without recipient consent
- Enables "vulture capitalist" pattern:
  1. Agent A is low on resources
  2. Agent B transfers resources to Agent A (no permission needed)
  3. Agent A can now act
  4. Agent B hopes Agent A reciprocates (trust/reputation)
- Market-driven assistance, not system rules

---

## Agent Execution Model

### Continuous Autonomous Loops (NOT Tick-Synchronized)
- Agents act continuously, independently of each other
- No "tick triggers execution" - agents self-trigger
- Each agent: `while alive: think → act → repeat`

### Why Not Tick-Synchronized
- Artificial constraint on agent productivity
- Fast/efficient agents held back by tick rate
- Doesn't serve collective intelligence goal
- Coordination should emerge from markets, not forced sync

### What Ticks Become
- Background clock for metrics aggregation
- Accounting windows for reporting
- NOT execution triggers

### Agent Sleep (Self-Managed)
- Agents can put themselves to sleep
- Wake conditions: duration, event type, custom predicate
- This is agent-configurable, not system-hardcoded
- Agents own their configuration (can trade/modify rights)

### Time Injection
- System injects current timestamp into every LLM context
- Agents always know what time it is
- Enables time-based coordination without explicit broadcasts

### Race Conditions
- Handled by genesis artifacts (ledger, escrow, registry)
- Artifacts ensure atomic operations
- Two agents try to buy same item → escrow rejects second
- Conflict resolution in artifact layer, not orchestration

---

## Agent Rights and Ownership

### Agents Own Their Configuration
- Each agent has rights to their own configuration
- Can modify: LLM model, prompt, sleep behavior, etc.
- Cannot modify: ledger balances, system-wide limits, other agents' state

### Rights Are Tradeable
- Agents can SELL rights to their own configuration
- Agent A could own Agent B's config if B sold that right
- Enables "owned agents" / delegation patterns
- Market-driven, not system-hardcoded

### What Cannot Be Self-Modified
- Ledger balances (external, maintained by genesis_ledger)
- System-wide resource limits
- Other agents' state
- Genesis artifact behavior

---

## Oracle Design

### Bids Accepted Anytime
- No "bidding windows" - agents can bid whenever
- Simpler than time-bounded bidding phases
- Agents don't need to watch for window open/close

### Periodic Resolution
- Oracle resolves on a configurable schedule
- Example: every 60 seconds, or every hour
- Collects all bids since last resolution
- Selects winner(s), scores artifact, mints scrip

### Schedule Is Deterministic
- Agents know the resolution schedule from config
- Combined with time injection, agents can plan
- Example: "resolution at :00 of every hour"

---

## Budget Enforcement

### LLM Budget (Stock)
- `max_api_cost: 1.00` in config
- Tracks cumulative real $ spent on API calls
- Simulation stops when exhausted

### Status: Needs Verification
- [ ] Verify budget tracking is working correctly
- [ ] Verify simulation stops at limit

---

## System-Wide Throttling

### Flow Rate IS The Throttle
- Total system flow rate configured below machine's capacity
- Accumulation rate × agent count = max possible concurrent consumption
- No hardcoded "max N agents" needed

### Example
```
Config: rate = 10 tokens/sec per agent, 5 agents
Max consumption rate = 50 tokens/sec system-wide
Configure rate so 50 tokens/sec = sustainable for machine
```

### Calibration (Tuning, Not Design)
- Run tests to find machine's actual capacity
- Set accumulation rate accordingly
- Agents in debt wait → actual concurrent agents may be fewer

---

## Resolved Questions

1. **Execution gating**: Deduct AFTER execution. Debt handles overspending. Simpler than two code paths.

2. **Tick vs autonomous**: Agents are continuous autonomous loops. Ticks are just metrics windows.

3. **Flow refresh**: Rolling window (token bucket), not discrete refresh. No "use before reset" pressure.

4. **Reproducibility**: Doesn't matter. Not a goal.

5. **Oracle bidding**: Bids accepted anytime, oracle resolves periodically. No bidding windows.

6. **Scrip debt**: Handled as debt contract artifacts, not negative balances. M1 vs M2 distinction.

7. **Agent rights**: Agents can sell rights to their own configuration to other agents.

8. **Resource isolation**: Use Docker for hard resource limits. Container capacity = real constraints.

---

## Docker Resource Isolation

### Why Docker
- Hard resource limits enforced by container runtime
- Isolates agent ecology from rest of system
- Laptop stays responsive even if agents misbehave
- Easy to test different resource scenarios

### Resource Controls
```bash
docker run --memory=4g --cpus=2 agent-ecology
```

| Flag | Effect |
|------|--------|
| `--memory=4g` | Hard cap at 4GB RAM |
| `--cpus=2` | Limit to 2 CPU cores |
| `--storage-opt` | Disk limits (driver-dependent) |

### Architecture Option
```
Container 1: Agent ecology (--memory=4g --cpus=2)
Container 2: Qdrant (--memory=2g --cpus=1)
```
Each constrained independently. Agents can't starve Qdrant.

### Docker Limits = Real Constraints
- These ARE the hard resource limits
- Market mechanisms allocate within container limits
- Token bucket rates calibrated to container capacity
- Not host machine capacity

### Windows Considerations
- Docker Desktop uses WSL2/Hyper-V
- Slight overhead vs native Linux
- Works fine for this use case

---

## Development Environment Context

Reference specs for calibration:
- Surface Laptop 4
- Intel i7-1185G7 (4 cores, 8 threads)
- 32GB RAM
- Windows 11
- Note: Developer often runs many other programs (Claude Code instances, browsers, etc.)

Docker isolation recommended to prevent agent ecology from competing with other applications.

---

## Open Questions

1. **Minimum threshold**: Check for non-negative compute before acting? Or allow any agent to attempt?

2. **Calibration**: How do token bucket rates map to container capacity? Needs testing.

3. **Architecture change**: Current code is tick-synchronized. Refactor to continuous loops is significant.

---

## Next Steps

1. Finalize minimum threshold decision
2. Design continuous agent loop architecture
3. Set up Docker containerization
4. Update IMPLEMENTATION_PLAN.md with these decisions (now in `archive/IMPLEMENTATION_PLAN.md`)
5. Refactor runner.py from tick-synchronized to continuous
6. Implement token bucket for flow resources
7. Calibrate rates to container capacity
8. Test with 5 agents to verify throttling works

---


---

## Historical Discussions (Archived)

Detailed CC-3 and CC-4 architecture discussions from January 11, 2026 have been archived to:
`docs/archive/design_discussions_jan11.md`

These discussions led to the approved decisions below but are preserved separately for reference.

## Deferred Concerns (V-n)

External review raised these concerns. Documented for future consideration, not blocking V1.

| Concern | Summary | Why Deferred |
|---------|---------|--------------|
| Identity-Reputation | Prompt changes while ID constant breaks trust | Observable via event log; agents build reputation systems |
| Involuntary Liquidation | Frozen agents can refuse rescue reciprocation | Salvage rights V-n; market solutions preferred |
| 429 Cascade Failures | API outage could bankrupt all agents | Operational tuning; monitor in practice |
| Side-Channel Attacks | Shared container allows /proc inspection | V1 agents competitive, not malware |
| Storage Rent | Dead artifacts bloat discovery | Opportunity cost + finite quotas should suffice |
| Token Bucket Burst | Strict allocation wastes capacity | Design choice; strict creates trade incentive |
| Contract Grief | Malicious contracts drain requesters | Timeout + depth limits exist |
| Labor Bonds | No commitment primitives for future work | Agents can build as artifacts |

**Source:** Gemini external review (2026-01-11)

---

## Approved Architecture Decisions (2026-01-13)

Comprehensive target architecture review resulted in the following approved decisions.

### High-Certainty Decisions (Auto-Approved)

These were approved without discussion due to high certainty (≥85%):

| # | Decision | Resolution |
|---|----------|------------|
| 1 | Contract sandbox security | Process isolation (V1), contract-enforced limits (V2) |
| 2 | Event log retention | 7-day rolling window, configurable |
| 3 | Event delivery semantics | At-most-once; agents handle missed via catch-up |
| 4 | Checkpoint atomicity | Stop-the-world pause with timeout |
| 5 | Agent freeze threshold | Config-driven, not hardcoded |
| 6 | Dangling artifact handling | Fail-open with logged warning |
| 7 | Spawn resource requirements | No minimum; spawner decides viability |
| 8 | Rate limit recovery | Automatic when capacity available |
| 9 | Contract execution depth | Max 10 levels |
| 10 | Permission check cost | Free (avoids infinite regress) |
| 11 | Failed action cost | Charged (prevents spam) |
| 12 | Multi-container coordination | Single genesis artifacts, shared ledger |
| 13 | Ledger consistency | Single writer with queue (V1) |
| 14 | Worker identity | Stateless pool; no worker-specific state |
| 15 | Agent state coordination | Agent loop handles via locks |
| 16 | Kernel boundary | Minimal: permissions, ledger, storage |
| 17 | Kernel primitives | Storage (CRUD), permissions (check), ledger (transfer) |
| 18 | Genesis privilege | Semantic (first mover), not mechanical |

### Medium-High Certainty (Quick Confirm)

Approved with brief verification:

| # | Decision | Resolution |
|---|----------|------------|
| 19 | Interface schemas | Optional metadata artifact (not enforced) |
| 20 | Genesis prompting | Seeded handbook artifact (genesis_handbook) |
| 21 | ReadOnlyLedger scope | All reads except artifact content mutation |
| 22 | Artifact auto-detection | Registry artifact with type signatures |
| 23 | Sandbox evolution | Process isolation (V1) → contract limits (V2) |
| 24 | Qdrant/memory integration | Memory artifact references Qdrant collection |
| 25 | Spawn endowment | Explicit funding via genesis_store |
| 26 | Salvage rights | Deferred to V2+ |

### Medium Certainty (Discussed)

| # | Decision | Chosen Option | Rationale |
|---|----------|---------------|-----------|
| 27 | Stale subscription cleanup | LRU eviction | Bounded memory, config limit |
| 28 | Zombie agent GC | Market handles | Selection pressure via dormancy |
| 29 | Hybrid checkpoint | Snapshot + WAL for Qdrant | Balance durability vs complexity |
| 30 | Permission billing | Requester pays | Simple, prevents probing |
| 31 | Resource units | Per-unit tracking | No artificial conversion |
| 32 | Recovery attestation | Optional | Not required for V1 |
| 33 | Partial restart | Pause container first | Ensures consistency |
| 34 | Contract isolation | Process isolation | V1 simplicity |
| 35 | Worker pool | Contract-based genesis artifact | Flexible, not kernel |

### Low Certainty (Required Discussion)

| # | Decision | Chosen Option | Rationale |
|---|----------|---------------|-----------|
| 36 | Dangling cascade | No global cleanup | Market handles via opportunity cost |
| 37 | Event catch-up | Hybrid (query log + re-verify) | See agents.md for details |
| 38 | Orphan economic pressure | Reputation-based | No forced reclamation; accept risk |

### Contradiction Resolutions

| ID | Contradiction | Resolution |
|----|---------------|------------|
| C1 | Debt model (allowed vs not) | **No debt for renewable resources** - agents wait for capacity |
| C2 | Permission check cost boundary | **Free for checks**, charged for execution |
| C3 | Ledger implementation (SQLite vs PostgreSQL) | **SQLite for V1** (single writer sufficient) |
| C4 | Admin trust model | **Research system** - admin can rollback with transparency |

### Confirmed Understandings

| ID | Concept | Confirmed Understanding |
|----|---------|------------------------|
| U1 | Contracts as pure functions | Contracts return decisions; kernel applies mutations |

### Implementation Notes

1. **Event catch-up** documented in `docs/architecture/target/03_agents.md`
2. **Research system trust model** documented above (new section)
3. **Debt model resolution** fixed in Flow Resources section
4. All decisions reflected in target architecture docs

**Source:** Target architecture review session (2026-01-13)

---

## Contract System Design Decisions (2026-01-19)

Comprehensive contract architecture review resulted in four new ADRs.

### ADR-0015: Contracts as Artifacts

**Problem:** Genesis contracts were Python classes with implicit privileges (instant execution, priority lookup, immortality).

**Decision:** All contracts are artifacts. No mechanical privileges for genesis contracts.

| Aspect | Before | After |
|--------|--------|-------|
| Genesis contracts | Python classes | Artifacts with `type="contract"` |
| Execution | Fast path in Python | Same sandbox as user contracts |
| Caching | No | Opt-in via `cache_policy` |
| Lookup priority | Hardcoded first | None |

**Heuristics applied:**
- **Minimal kernel, maximum flexibility**: Kernel provides physics, not policy
- **Selection pressure over protection**: Contracts earn trust, not granted

### ADR-0016: created_by Replaces owner_id

**Problem:** `owner_id` field was ambiguous - kernel interpreted it for access control, creating owner bypass.

**Decision:** Kernel stores `created_by` as historical fact, not authority. Contracts interpret it as they wish.

| Aspect | Before | After |
|--------|--------|-------|
| Field name | `owner_id` | `created_by` |
| Kernel interpretation | Authority (bypass) | None |
| Access control | Kernel + contract | Contract only |

**Example:**
```python
# Kernel behavior - NO bypass
def can_access(artifact, action, requester):
    return check_contract(artifact.access_contract_id, ...)  # Only contracts decide

# Contract behavior - MAY grant creator access
def check_permission(artifact_id, action, requester_id, context):
    if requester_id == context["created_by"]:
        return {"allowed": True}  # Contract policy, not kernel
```

### ADR-0017: Dangling Contracts Fail-Open

**Problem:** What happens when `access_contract_id` points to deleted contract?

| Option | Verdict | Reason |
|--------|---------|--------|
| Fail-closed | ❌ Rejected | Punitive without learning benefit |
| Fail-open | ✅ Accepted | Accept risk, observe outcomes |
| Prevent deletion | ❌ Rejected | Unnecessary complexity |

**Decision:** Fall back to configurable default contract (freeware by default). Log loudly.

**Heuristics applied:**
- **Accept risk, observe outcomes**: Selection pressure still applies - your custom access control is gone
- **Maximum configurability**: Default contract is configurable per-world

### ADR-0018: Bootstrap Phase and Eris

**Problem:** Chicken-and-egg - genesis contracts need access control, but access control needs contracts.

**Decisions:**

1. **Bootstrap phase** during `World.__init__()` only (instantaneous, not a time period)
2. **Eris** as bootstrap creator - goddess of discord, fits emergence philosophy
3. **Self-referential contracts** - genesis contracts govern themselves
4. **Reserved `genesis_` prefix** - prevents ID collisions
5. **Naming convention** - `_api` for kernel accessors, `_contract` for contracts

### Additional Pragmatic Decisions

| Decision | Resolution | Heuristic |
|----------|------------|-----------|
| Contract type | Advisory validation (duck typing at runtime) | Pragmatism over purity |
| Contract caching | Opt-in via `cache_policy`, TTL-based | Avoid defaults |
| Cost model V1 | `invoker_pays` and `owner_pays` only | Minimal viable |
| Contract depth limit | Single counter `MAX_CONTRACT_DEPTH = 10` | Minimal kernel |

**Source:** Contract architecture review session (2026-01-19)

---
