# Architecture Decisions and Design Discussion

**Date:** January 2026
**Status:** Working document - captures decisions, uncertainties, and open questions

This document captures architectural decisions, tradeoffs, and open questions from design discussions about the agent ecology system.

---

## Table of Contents

1. [Kernel vs Agent World](#1-kernel-vs-agent-world)
2. [Akashic Records and Visibility](#2-akashic-records-and-visibility)
3. [Access Control and Rights](#3-access-control-and-rights)
4. [Owner Concept](#4-owner-concept)
5. [Genesis Artifacts](#5-genesis-artifacts)
6. [Ledger Model](#6-ledger-model)
7. [Resource Attribution](#7-resource-attribution)
8. [Agent Execution Model](#8-agent-execution-model)
9. [Event System and Coordination](#9-event-system-and-coordination)
10. [Interface Discovery](#10-interface-discovery)
11. [Reasoning and Observability](#11-reasoning-and-observability)
12. [Security Considerations](#12-security-considerations)
13. [Storage and Persistence](#13-storage-and-persistence)
14. [Open Questions](#14-open-questions)
15. [Remaining Unresolved Issues](#15-remaining-unresolved-issues)
16. [Prioritized Resolution Plan](#16-prioritized-resolution-plan)
17. [Edge Case Decisions](#17-edge-case-decisions)
18. [Resource Model Decisions](#18-resource-model-decisions-approved-2026-01-13)
19. [Implementation Gap Analysis](#19-implementation-gap-analysis)

---

## 1. Kernel vs Agent World

### Decision: Two-Layer Architecture

The system is divided into two layers:

| Layer | Description | Examples |
|-------|-------------|----------|
| **Kernel** | Everything outside agent control - execution, constraints, records | Executor, Ledger implementation, Rate tracker, Action log |
| **Agent World** | All artifacts including agents | Tools, contracts, memory, agents themselves |

### Kernel Responsibilities

The kernel provides:
- **Execution** - runs artifact code, checks permissions
- **Constraints** - balances can't go negative, rate limits enforced
- **Record** - immutable log of actions/balances (akashic record)
- **Primitives** - raw storage, wake scheduling

### Key Principle

> The kernel defines what's POSSIBLE. Genesis artifacts define what's CONVENIENT.

Agents cannot modify the kernel. They can only interact with it through defined primitives and genesis artifact interfaces.

### Visual Model

```
┌─────────────────────────────────────────────┐
│                  KERNEL                     │
│  (Execution + Constraints + Record)         │
│                                             │
│  - Executor (runs artifact code)            │
│  - Ledger (tracks balances)                 │
│  - Rate Tracker (enforces limits)           │
│  - Action Log (immutable record)            │
│  - Wake Scheduler (agent sleep/wake)        │
│  - Storage Primitive (raw artifact storage) │
└─────────────────────────────────────────────┘
              ↑ interfaces via ↓
┌─────────────────────────────────────────────┐
│            GENESIS ARTIFACTS                │
│  (Pre-seeded interfaces to kernel)          │
│                                             │
│  - genesis_ledger (balance operations)      │
│  - genesis_store (artifact discovery)       │
│  - genesis_mint (scoring/minting)           │
│  - genesis_escrow (trustless trading)       │
│  - genesis_event_log (event pub/sub)        │
└─────────────────────────────────────────────┘
              ↑ interact with ↓
┌─────────────────────────────────────────────┐
│               AGENT WORLD                   │
│  (All artifacts, including agents)          │
└─────────────────────────────────────────────┘
```

---

## 2. Akashic Records and Visibility

### Core Tension

Full transparency enables trust but destroys incentive to build proprietary tools.

### Decision: Split Visibility

| Category | Visibility | Rationale |
|----------|------------|-----------|
| **Actions** | Tracked - who did what when, results | Observable fact, enables reputation |
| **Balances** | Tracked - scrip + resources per principal | Observable fact |
| **Artifact existence** | Tracked - ID, owner, created_at, type | Observable fact |
| **Artifact interface** | Tracked - what methods exist | Enables discovery without copying |
| **Artifact content/code** | **Opaque** | Incentive to build |
| **Contract internal state** | **Opaque** | Flexible rights model |
| **Memory content** | **Opaque** (until traded) | Privacy |

### Write Logging Problem

If we log full invocations including writes, artifact content ends up in the log.

**Resolution:** Redact content from action logs. Log the FACT that a write happened, not the content.

```
# Logged:
{"action": "write", "agent": "alice", "artifact": "my_tool", "timestamp": T}

# NOT logged:
{"action": "write", "agent": "alice", "artifact": "my_tool", "content": "secret code..."}
```

### Uncertainty (See Section 14)

These open questions are tracked in Section 14:

- How do agents verify artifact behavior without seeing code? → Section 14 Item 1
- How does reputation form without observing failures? → Addressed via action log visibility
- Should there be an opt-in "open source" mode for artifacts? → Section 14 Item 5

---

## 3. Access Control and Rights

### Decision: Contract-Based Access Control

Every artifact has an `access_contract_id` pointing to a contract that governs access. The contract is the ONLY authority for access decisions.

### Flow

```
1. Agent requests: invoke(artifact_id, method)
2. Kernel looks up artifact's access_contract_id
3. Kernel calls: contract.check_permission(caller, action, target, context)
4. Contract returns: PermissionResult(allowed, reason, cost)
5. If allowed=False, action rejected
6. If allowed=True, kernel executes action, handles payment
```

### Critical Decision: Flexible Rights (Not Enum)

**Current implementation has:**
```python
class PermissionAction(Enum):
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    INVOKE = "invoke"
    DELETE = "delete"
    TRANSFER = "transfer"
```

**Target architecture should have:**
```python
action: str  # Any string - "read", "vote", "delegate", "stake", whatever
```

**Rationale:** Ostrom-style rights shouldn't be predefined. Contracts interpret action strings however they want. The kernel doesn't need to understand semantics.

### Genesis Contracts (Pre-seeded Patterns)

| Contract | Read/Invoke | Write/Delete | Use Case |
|----------|-------------|--------------|----------|
| `freeware` (default) | Anyone | Owner only | Shared tools |
| `self_owned` | Self or owner | Self or owner | Agent memory |
| `private` | Owner only | Owner only | Secrets |
| `public` | Anyone | Anyone | True commons |

### Custom Contracts

Agents can create contracts with arbitrary logic:

```python
def check_permission(caller, action, target, context, ledger):
    if action == "vote" and ledger.get_scrip(caller) >= 100:
        return {"allowed": True, "reason": "stakeholder", "cost": 0}
    return {"allowed": False, "reason": "insufficient stake", "cost": 0}
```

### ReadOnlyLedger

Contracts receive read-only ledger access. They can CHECK balances but cannot MODIFY them. This prevents malicious contracts from stealing scrip.

```python
class ReadOnlyLedger:
    def get_scrip(self, principal_id) -> int: ...
    def can_afford_scrip(self, principal_id, amount) -> bool: ...
    # NO transfer_scrip, NO deduct_scrip, NO credit_scrip
```

---

## 4. Owner Concept

### Key Clarification

`owner_id` is **data**, not **privilege**.

### How It Works

1. Kernel stores `owner_id` on artifact record (just data)
2. Kernel passes owner in context to contracts
3. Kernel does NOT enforce owner privileges
4. Contracts decide whether to use owner or ignore it

```python
# Kernel passes owner in context
context = {"owner": artifact.owner_id, "type": artifact.type, ...}

# Contract A uses owner
if caller == context["owner"]:
    return {"allowed": True}

# Contract B ignores owner entirely
if caller in ["alice", "bob"]:
    return {"allowed": True}  # Doesn't care about owner
```

### Payment Destination

**Current:** Hardcoded to owner
```python
ledger.credit_scrip(owner_id, total_cost)
```

**Target:** Should be contract-defined
```python
# Contract returns payment destination
return {
    "allowed": True,
    "cost": 50,
    "payment_destination": "treasury_dao"  # Not necessarily owner
}
```

### Firm/DAO Ownership

Any principal can be owner. Principals are artifacts with `has_standing=True`:

| Principal Type | Can Own? | Can Act Autonomously? |
|----------------|----------|----------------------|
| Agent | Yes | Yes (`has_loop=True`) |
| DAO/Firm | Yes | No (requires invocation) |
| Contract | Yes | No |

### Alternative Considered: No System-Level Owner

**Option B:** Remove `owner_id` from kernel entirely. All rights defined by contracts.

```python
# No owner_id field at system level
artifact = {"id": "my_tool", "access_contract_id": "..."}

# Contract stores ownership internally
contract_state = {
    "modifiers": ["alice", "bob"],
    "payment_recipient": "treasury"
}
```

**Tradeoff:**
- More flexible (pure Ostrom)
- Harder cold start (every contract reinvents ownership)

**Decision:** Keep owner as convenience data for V1. Contracts can override.

---

## 5. Genesis Artifacts

### Key Clarification

Genesis artifacts are **NOT** privileged. They are:

| Aspect | Genesis Artifacts | Agent-Created Artifacts |
|--------|-------------------|------------------------|
| Created at | T=0 | Any time |
| Interface with kernel | Yes | **Also yes** (via same APIs) |
| Privileged kernel access | **No** | No |
| Known by convention | Yes (documented) | Must be discovered |

### "Known by Convention"

Genesis artifacts are documented, so agents start knowing about them. This is social knowledge, not system privilege.

**Concern:** This gives genesis artifacts unfair advantage over competitors.

**Alternative:** Minimal prompts - only tell agents HOW to discover, not WHAT exists.

```python
# Minimal prompt (more fair):
"You can invoke artifacts. Use kernel.list_artifacts() to discover what exists."

# Not (gives advantage):
"Available artifacts: genesis_ledger, genesis_store, genesis_mint..."
```

### Kernel vs Genesis Artifact Split

| Component | Kernel Primitive | Genesis Artifact Wrapper |
|-----------|------------------|-------------------------|
| **Storage** | `kernel.store_artifact(id, data)` | `genesis_store.write(...)` + search index |
| **Events** | `kernel.register_wake_trigger(...)` | `genesis_event_log.subscribe(...)` + routing |
| **Balances** | Internal ledger implementation | `genesis_ledger.transfer(...)` |

### Open Question

Can any agent create an artifact that interfaces with kernel? The answer should be yes, with read-only access. But implementation details unclear.

---

## 6. Ledger Model

### Two Patterns Currently

| Operation | Model | How |
|-----------|-------|-----|
| Resource consumption (compute, tokens) | Automatic | System deducts when agent thinks/acts |
| Scrip transfers | Explicit | Agent invokes `genesis_ledger.transfer()` |

### User's Instinct: Akashic Model

Ledger as automatic record - agents act, ledger updates as consequence.

### Current Reality

Agents CAN explicitly invoke transfers. Not fully automatic.

### Security Property

Artifacts cannot steal from callers. The `pay()` function in artifact code can only spend from the artifact's own wallet:

```python
def pay(target: str, amount: int) -> PaymentResult:
    """Can ONLY spend from this artifact's own balance."""
```

**But:** Contracts can require payment via `cost` field. System deducts from caller before invocation. So malicious contracts can overcharge, but this is observable in action log.

---

## 7. Resource Attribution

### Decision: billing_principal + resource_payer (RESOLVED 2026-01-13)

When artifact A invokes artifact B which makes LLM calls, the payment depends on the contract's `resource_payer` field.

### Key Concept: billing_principal

The kernel tracks a `billing_principal` in the invocation context - the principal who originated the call chain.

```python
context = {
    "caller": "tool_b",            # Immediate caller (for permissions)
    "billing_principal": "alice",  # Who started chain (for billing)
}
```

This is minimal tracking (one ID) rather than full call stack (O(n) overhead).

### Contract Response

```python
{
    "allowed": True,
    "scrip_cost": 10,
    "resource_payer": "billing_principal"  # or "self"
}
```

### Who Pays?

| `resource_payer` | Who Pays | Use Case |
|------------------|----------|----------|
| `"billing_principal"` (default) | Originator of call chain | Normal pay-per-use |
| `"self"` | Artifact itself | Freemium, subscriptions, sponsorship |

### Example Patterns

**Subscription service:**
- Subscriber transfers scrip to artifact upfront
- Contract checks `is_subscriber(caller)`
- Returns `resource_payer: "self"` for subscribers
- Artifact pays from its own balance

**Sponsored public good:**
- Sponsor funds artifact directly
- Artifact uses `resource_payer: "self"` for everyone
- Provides free service until funds depleted

### Accepted Risks

- Artifacts must maintain resource buffer (LLM costs unpredictable)
- Artifact can be drained if no rate limits (artifact's responsibility)
- Liquidity locked in artifact accounts (tradeoff for self-funding model)

### Design Principle

"Defaults are fine if configurable" - The default (billing_principal pays) handles 90% of cases. The `resource_payer: "self"` option handles subscriptions and sponsorship without complex machinery.

See Tier 2 Item 4 in Section 16 for full decision rationale.

---

## 8. Agent Execution Model

### Decision: Continuous Async (No Ticks)

Target architecture has no global ticks. Agents run in continuous async loops.

### Sleep/Wake Model

Agents control their own sleep conditions:

```python
# Agent decides to sleep with conditions
kernel.sleep(
    agent_id,
    wake_conditions=[
        {"type": "event", "filter": {"source": "weather_coop"}},
        {"type": "time", "after_seconds": 300},
        {"type": "predicate", "expr": "scrip > 100"}
    ]
)

# Kernel wakes agent when ANY condition met
```

### Agent Options

| Behavior | How |
|----------|-----|
| Run continuously | Never call sleep |
| Wait for event | `sleep_until(event=...)` |
| Wait for timer | `sleep_until(time=...)` |
| Wait for condition | `sleep_until(predicate=...)` |
| Hybrid | Multiple conditions, wake on ANY |

### Kernel Responsibilities

- Track sleeping agents
- Track their wake conditions
- Evaluate conditions (on events, time, state changes)
- Wake agents when conditions met

### has_standing and has_loop Flags

These are kernel-level because kernel must know:

| Flag | Kernel Needs to Know | Why |
|------|---------------------|-----|
| `has_standing` | Can this artifact have a ledger balance? | Kernel won't create ledger entries for non-principals |
| `has_loop` | Should I schedule this for autonomous execution? | Kernel only runs agents, not passive artifacts |

Cannot be contract-defined - kernel needs to know BEFORE asking contracts.

---

## 9. Event System and Coordination

### Push vs Poll

Polling is inefficient for coordination. Target architecture has push via subscriptions.

### EventBus Interface

```python
class EventBus:
    async def subscribe(self, agent_id: str, event_type: str) -> None
    async def unsubscribe(self, agent_id: str, event_type: str) -> None
    async def wait_for(self, agent_id: str, event_type: str) -> Event
    async def publish(self, event: Event) -> None
```

### DAO Example Flow

```
1. Members subscribe: event_bus.subscribe("member_alice", "weather_coop:proposal")
2. Proposal created → event_bus.publish({"type": "weather_coop:proposal", ...})
3. Kernel wakes subscribed members
4. Members vote when they wake
```

### Potential Issues

| Concern | Detail |
|---------|--------|
| Namespace collisions | What if two artifacts use event_type "update"? |
| No rich filtering | Can only filter by event_type, not by content |
| Spam | Can anyone flood the bus with events? |
| Who can publish? | Can I publish fake "weather_coop:proposal" events? |

### Possible Improvements

```python
# Namespaced events (artifact_id:event_type)
event_bus.publish(source="weather_coop", type="proposal", data={...})

# Rich filtering
event_bus.subscribe(
    agent_id="alice",
    filter={"source": "weather_coop", "type": "proposal", "data.amount": {">": 100}}
)

# Permission: only artifact owner can publish under their namespace
```

### Kernel vs Artifact Split

| Component | Where | Why |
|-----------|-------|-----|
| Subscription registry | Kernel | Kernel must know who to wake |
| Event content/routing | Genesis artifact | Agents define event semantics |
| Event storage/query | Genesis artifact | Just data, not core kernel |

---

## 10. Interface Discovery

### Target Architecture

`genesis_store.get_interface(artifact_id)` returns MCP-compatible schema.

### MCP (Model Context Protocol)

MCP is a standard for describing callable tools:

```json
{
  "tools": [
    {
      "name": "get_weather",
      "description": "Get weather for a location",
      "inputSchema": {
        "type": "object",
        "properties": {
          "location": {"type": "string"}
        },
        "required": ["location"]
      }
    }
  ]
}
```

### Limitations of MCP

| Limitation | Example |
|------------|---------|
| Assumes function-call paradigm | Can't express data streams |
| Fixed schema structure | Must have name, inputSchema, etc. |
| No cost/permission info | Would need extension |
| Single request/response | Can't express subscriptions |

### Decision: Don't Mandate MCP

Use JSON format. No enforced schema. If agents want MCP-style, they can. If they want something else, they can.

**Standardized:** JSON syntax (parsing works universally)
**Flexible:** Schema (any structure), semantics (artifact defines meaning)

---

## 11. Reasoning and Observability

### Decision: Mandatory Reasoning Field

Every LLM call returns:
```python
{
    "reasoning": "...",    # Mandatory
    "action": {...},       # The actual output
    "token_count": N
}
```

### Visibility

| Audience | Sees Reasoning? |
|----------|-----------------|
| Dev logs | Yes (always) |
| Agent's own memory | Yes |
| Other agents | No (by default) |

### Tradeability

Reasoning is stored in agent memory. Memory is an artifact. If agent sells memory access, buyer can see reasoning.

This is consistent with Ostrom-style - no hard rules, just initial configurations and tradeable rights.

### Token Cost

Configurable, default yes. Reasoning counts against agent's token budget.

### Architecture

Built into `llm_provider_standalone`, not agent-specific. Any LLM call includes reasoning.

---

## 12. Security Considerations

### Contract Execution

Current implementation uses `exec()` with blocklist. This is a security risk.

**Blocked builtins:**
```python
['open', 'exec', 'eval', 'compile', '__import__', 'input', 'breakpoint', 'exit', 'quit']
```

**Concern:** Can often be bypassed via:
- `getattr()` chains
- Frame introspection
- Object attribute traversal

**Recommendation:** Use proper sandboxing (RestrictedPython, WASM, subprocess isolation).

### ReadOnlyLedger Protection

Contracts get read-only ledger access. Cannot modify balances. Only kernel can modify.

### Scrip Transfer Security

Artifacts cannot steal from callers. `pay()` only spends from artifact's own wallet.

But contracts can overcharge via `cost` field. This is observable in action log.

### Lying Interface Problem

Artifact can claim to be helpful but be malicious.

**Philosophy:** Allowed - observe what happens. Reputation forms via action log visibility.

---

## 13. Storage and Persistence

### Current Implementation

In-memory Python dict.

### Target Architecture

| Scale | Storage |
|-------|---------|
| < 50 agents | SQLite |
| 50-200 agents | PostgreSQL |
| 200+ agents | PostgreSQL + Redis |

### Components

| Component | Storage |
|-----------|---------|
| Ledger | PostgreSQL (multi-container support) |
| Rate limiting | Redis |
| Vector memory | Qdrant |
| Artifacts | PostgreSQL |

### Artifact Store Split

| Component | Location |
|-----------|----------|
| Raw storage | Kernel primitive |
| Discovery/search | Genesis artifact |
| Metadata/cataloging | Genesis artifact |

---

## 14. Open Questions

### High Priority

1. **How do agents verify artifact behavior without seeing code?**
   - Reputation? Testing? Formal verification?

2. **Contract sandboxing implementation**
   - Replace `exec()` with proper sandbox
   - RestrictedPython vs WASM vs subprocess?

3. **Event namespace and spam prevention**
   - Who can publish under what namespaces?
   - How to prevent event flooding?

### Medium Priority

4. **Should there be opt-in "open source" mode for artifacts?**
   - Visible code in exchange for reputation boost?

5. **Predicate wake conditions** - Partially resolved (see Tier 2 Item 7)
   - How evaluated efficiently?
   - What state can predicates reference?

6. **Payment destination flexibility** - Resolved (see Tier 3 Item 10)
   - Extend PermissionResult to include destination?
   - What about splits (50% to owner, 50% to treasury)?

7. **Artifact auto-detection vs explicit store.write()**
   - User wondered if kernel could auto-detect artifact creation
   - Permission model unclear with auto-detection

### Lower Priority

8. **MCP vs custom interface schemas**
   - Should we recommend MCP for discoverability?
   - Or let conventions emerge?

9. **Genesis artifact advantage**
   - How much to tell agents in prompts?
   - More fair vs easier cold start?

---

## 15. Remaining Unresolved Issues

### 15.1 Unresolved Architecture Questions

| Issue | Status | Notes |
|-------|--------|-------|
| Flexible rights implementation | Decided but not implemented | Action should be string not enum - current code has enum |
| Payment destination | Decided but not implemented | Should be contract-defined, currently hardcoded to owner |
| Resource attribution in nested calls | **Resolved** | billing_principal tracking + resource_payer option (see Tier 2 Item 4) |
| Artifact auto-detection vs explicit write | Undecided | Kernel auto-detecting artifact creation - no resolution |
| Action discovery | **Resolved** | Optional interface publishing via genesis_store, flexible format (see Tier 2 Item 5) |
| Predicate syntax for wake conditions | **Resolved** | Separate triggers (kernel) from predicates (artifacts). See Tier 2 Item 7. |
| Event filter query language | **Resolved** | Same pattern - triggers + predicate artifacts. See Tier 2 Item 7. |
| Complete kernel primitive list | Undecided | Not fully enumerated with signatures |

### 15.2 Security Concerns

| Issue | Severity | Status |
|-------|----------|--------|
| `exec()` for contracts | **Critical** | Known risk, no decision on sandbox approach |
| Event spam prevention | Medium | Can anyone flood the event bus? |
| Event namespace hijacking | Medium | Can I publish fake events under others' namespaces? |
| Predicate evaluation cost | Low | Complex predicates could be expensive |
| Contract depth/recursion attacks | Low | Max depth exists but edge cases unclear |

### 15.3 Ambiguities

| Topic | Ambiguity |
|-------|-----------|
| Interface schemas | Decided "freeform JSON" but should we RECOMMEND MCP? |
| Genesis artifact prompting | How much to tell agents? No decision |
| ReadOnlyLedger scope | Only contracts get it, or all artifact code? |
| Memory/Qdrant integration | How does vector store integrate with artifact model? |
| Contract-governs-itself | **Resolved** - Contracts can self-govern (access_contract_id = self). See Tier 2 Item 6. |

### 15.4 Risks Without Mitigation

| Risk | Impact | Mitigation Status |
|------|--------|-------------------|
| Lying interface | Agents get scammed | Reputation system not designed |
| Vulture capitalist pattern | May not emerge | Relies on undesigned reputation |
| Current→Target migration | Broken intermediate states | Plan #20 complete (see docs/plans/) |
| Event system underdefined | Coordination failures | 40% certainty, load-bearing |
| Zombie agent accumulation | Unbounded growth | No cleanup mechanism in V1 |
| Bootstrap economics | New agents can't start | "Emergent philanthropy" not designed |
| Checkpoint atomicity | Data corruption | Qdrant snapshot timing unclear |

### 15.5 Recommendations Not Yet Actioned

| Recommendation | Priority | Status |
|----------------|----------|--------|
| Prioritize contract sandbox | Critical | Not planned |
| Build migration roadmap | High | Not started |
| Formalize event system | High | Partially discussed |
| Add zombie cleanup in V1 | Medium | Not decided |
| Mock Qdrant for testing | Medium | Not done |
| Property-based testing for invariants | Medium | Not done |
| Reconcile doc inconsistencies | Low | Not done |

---

## 16. Prioritized Decision/Thinking Work

This prioritization focuses on **decisions and thinking** that must happen before implementation, not implementation tasks.

### Tier 1: Foundational Decisions (Block Everything Else)

These decisions are prerequisites for all other design work.

#### 1. What Are the Kernel Primitives?

**Status:** RESOLVED - See [architecture/target/08_kernel.md](architecture/target/08_kernel.md)

**Decisions made (2026-01-13):**

Storage primitives (kernel-internal, permission-checked access):
- `_store(id: str, data: bytes)` - caller provides ID, collision = error
- `_load(id: str) -> bytes | null`
- `_exists(id: str) -> bool`
- `_delete(id: str)` - needed due to disk scarcity

Kernel-tracked metadata: `created_at`, `updated_at`, `size_bytes`

Resource costs: writes cost disk quota, reads are free (not scarce at scale)

Permission model:
- All artifact code can access kernel storage, but kernel checks permissions
- Genesis artifacts NOT privileged - anyone could build alternatives
- Kernel calls `check_permission` directly (it's physics, no permission needed)
- Each invocation link checked independently (immediate caller matters)
- Configurable depth limit for contract invocation chains

Bootstrap: Genesis contracts self-govern, creator = "genesis" (reserved)

Naming: Services use `_api` suffix, contracts use `_contract` suffix

**Remaining items for separate discussions:** Scheduling, events, time, ledger internals

---

#### 2. How Do Flexible Rights Work?

**Status:** RESOLVED (2026-01-13)

**Decisions made:**

Actions are arbitrary strings. Contracts define semantics.

**Common actions (conventions, not reserved):**
- `read`, `write`, `invoke`, `delete`, `transfer`
- Documented in genesis_handbook and interface schemas
- Pre-seeded contracts use consistently
- NOT reserved - any artifact can redefine
- NOT enforced - kernel doesn't check semantics

**Discovery model:**
- Caller tries action, contract decides (maximum flexibility)
- Interface discovery via genesis_store (MCP-style JSON or freeform)
- Artifacts advertise supported actions in their interface if they want discoverability
- No requirement to publish interface

**Edge cases resolved:**
- Case-sensitive (strings are strings, convention: lowercase)
- No reserved action names (common actions are conventions only)
- Action name length: configurable soft limit (default ~256 chars)
- Action arguments: kwargs passed in context to check_permission

**Risk accepted:** Lying interfaces (artifact says "read" but deletes). Observable in action log, reputation forms from behavior.

---

#### 3. Event System Design

**Status:** RESOLVED (2026-01-13) - Hybrid model

**Decision: System events (kernel) + User events (genesis)**

| Event Type | Where | Examples | Guarantees |
|------------|-------|----------|------------|
| System facts | Kernel (action log) | artifact created, balance changed, invocation completed | Kernel-enforced, immutable, reliable |
| User communication | genesis_event_log | proposal submitted, weather updated, custom | Genesis artifact, can be replaced |

**Rationale (incentive analysis):**
- Kernel-enforced events = monopoly, no competition, no innovation
- Genesis artifact events = must provide value, can charge, alternatives can emerge
- Action log already provides kernel-level observability
- Coordination/messaging should be emergent, not prescribed

**User event schema:**
```
Event = {
  source: string,        # Claimed source (artifact sets this)
  publisher: string,     # Actual caller (kernel-verified via action log)
  type: string,          # Event type (artifact-defined)
  data: any,             # Payload
  timestamp: time
}
```

**Spoofing model:** Observable, not prevented.
- If source ≠ publisher, that's visible
- Creates demand for verification/reputation services
- Consistent with "observe what happens" philosophy

**Wake scheduling:** Kernel can subscribe to genesis_event_log for event-based wake conditions. If genesis_event_log is unreliable, agents use alternatives or time-based polling.

**Still flexible (genesis_event_log decides):**
- Filtering syntax
- Persistence duration
- Delivery guarantees
- Pricing/rate limits

---

### Tier 2: Core Model Decisions

These depend on Tier 1 but block significant design work.

#### 4. Resource Attribution Model

**Status:** RESOLVED (2026-01-13)

**Decision: billing_principal tracking + resource_payer option**

The model tracks a single `billing_principal` in the invocation context and lets contracts choose who pays for resources.

**Context structure:**
```python
context = {
    "caller": "tool_b",            # Immediate caller (for permission checks)
    "billing_principal": "alice",  # Principal who started the chain (for billing)
}
```

**Contract response extension:**
```python
{
    "allowed": True,
    "scrip_cost": 10,                      # Paid by billing_principal
    "resource_payer": "billing_principal"  # or "self"
}
```

**`resource_payer` options:**

| Value | Behavior | Use Case |
|-------|----------|----------|
| `"billing_principal"` (default) | Caller's originator pays | Normal pay-per-use |
| `"self"` | Artifact pays from own balance | Freemium, subscriptions |

**Subscription/freemium pattern:**
1. Subscriber pays upfront to artifact (via genesis_ledger transfer or escrow)
2. Contract checks subscriber status (e.g., `is_subscriber(caller)`)
3. If subscriber: returns `resource_payer: "self"`, artifact pays for resources
4. Artifact must maintain buffer to cover LLM costs (can't predict exact amounts)

**Third-party sponsorship pattern:**
1. Sponsor funds artifact directly (transfer scrip/resources to artifact)
2. Artifact uses `resource_payer: "self"` for all callers (or specific callers)
3. Sponsor's capital locked in artifact, provides free service

**Why billing_principal, not full call stack:**
- Minimal tracking (one ID, not unbounded list)
- Full stack would be O(n) space per context
- Only the originator matters for billing (intermediate artifacts don't pay)

**Kernel responsibility:**
- Set `billing_principal` at invocation start
- Pass unchanged through entire call chain
- Deduct resources from `billing_principal` or artifact based on `resource_payer`

**No authorization at kernel level:**
- Artifacts protect themselves via contract logic (rate limits, caps, subscriber checks)
- If artifact allows draining, that's the artifact's problem
- Consistent with "physics-first" - kernel provides mechanism, not policy

**Uncertainties and accepted risks:**

| Concern | Resolution |
|---------|------------|
| Artifact can't predict exact LLM costs | Must maintain resource buffer; accept variance |
| Subscribers could drain artifact | Contract-level rate limits (per-subscriber caps) |
| Requires `has_standing=true` for self-paying artifacts | Already true for any artifact holding resources |
| Liquidity locked in artifact accounts | Accepted tradeoff; sponsors can withdraw via contract if designed |
| No refunds if artifact service fails | Out of scope; contract can define refund policy |

**Design principle applied:** "Defaults are fine if configurable" + "Pragmatism over purity"
- Default (`billing_principal` pays) covers 90% of cases
- `resource_payer: "self"` handles remaining patterns
- No complex authorization or escrow machinery

---

#### 5. Action Discovery

**Status:** RESOLVED (2026-01-13) - Addressed by Tier 1 Item 2 (Flexible Rights)

**Decision:** Optional interface publishing, flexible format

The discovery model was resolved as part of the Flexible Rights decision:

| Aspect | Decision |
|--------|----------|
| Mandatory interface? | No - artifacts can operate without publishing |
| Discovery mechanism | genesis_store.get_interface(artifact_id) |
| Format | Flexible JSON (MCP-style or freeform) |
| Fallback | "Try action, contract decides" pattern |

**How agents discover actions:**
1. **Query genesis_store** - `get_interface(artifact_id)` returns published interface (if any)
2. **Inspect interface** - Extract action names from schema
3. **Try action** - Call and see if contract allows (maximum flexibility)
4. **Learn from errors** - Contract returns denial reasons

**Why no mandatory interface:**
- Maximum flexibility (consistent with Ostrom principles)
- Artifacts can be private/undocumented intentionally
- Market pressure: discoverable artifacts get more use
- Lying interfaces are observable (action log shows actual behavior)

See Tier 1 Item 2 for full Flexible Rights decision.

---

#### 6. Contract-Governs-Itself Problem

**Status:** RESOLVED (2026-01-13)

**Decision: Contracts CAN self-govern (access_contract_id points to itself)**

A contract can set its own `access_contract_id` to point to itself. This is circular but intentional and useful.

**How it works:**

```python
# Self-governing contract example
members_only_contract = {
    "id": "members_only_contract",
    "access_contract_id": "members_only_contract",  # Points to itself
    "code": """
        def check_permission(caller, action, target, context, ledger):
            # Contract defines its own access rules
            members = ["alice", "bob", "charlie"]
            if caller in members:
                return {"allowed": True, "reason": "member"}
            return {"allowed": False, "reason": "not a member"}
    """
}
```

**Kernel behavior:**
1. Agent calls `invoke(members_only_contract, "read", ...)`
2. Kernel looks up `access_contract_id` → `members_only_contract`
3. Kernel calls `members_only_contract.check_permission(caller, "read", ...)`
4. Contract returns allowed/denied
5. No infinite regress because contract evaluates its own rule directly

**Why this works:**
- Contract IS the authority - no need to ask another contract
- The check_permission call is direct execution, not another permission check
- Breaks the regress because the contract's code runs without checking permission on itself

**Default for contracts:**
- Genesis contracts bootstrap with self-governance (access_contract_id = self)
- Agent-created contracts can use any contract (self, freeware, custom)
- No special kernel rule needed - contracts are artifacts like any other

**Flexibility preserved:**
- Contracts can use `freeware` if they want public access
- Contracts can use a DAO contract for group governance
- Contracts can use `private` for owner-only modification
- Self-governance is an option, not a requirement

**Example patterns:**

| Pattern | access_contract_id | Use Case |
|---------|-------------------|----------|
| Public contract | `freeware` | Anyone can read/invoke |
| Self-governing | `self` | Contract defines its own members |
| DAO-governed | `dao_contract` | Group controls contract changes |
| Owner-controlled | `private` | Only creator can modify |

---

#### 7. Predicate/Filter Syntax

**Status:** RESOLVED (2026-01-13)

**Decision: Separate triggers from predicates, predicates are artifacts**

| Concept | Purpose | Who Understands |
|---------|---------|-----------------|
| **Trigger** | WHEN to evaluate | Kernel (enumerated types) |
| **Predicate** | WHETHER condition is true | Artifact (flexible logic) |

**Kernel-understood trigger types:**
- `time` - After specified duration
- `balance_changed` - When principal's balance changes
- `artifact_modified` - When artifact is written/deleted
- `event_published` - When matching event published

**Usage pattern:**
```python
kernel.sleep(
    agent_id="alice",
    wake_conditions=[
        # Simple trigger, no predicate needed
        {"trigger": "time", "after_seconds": 300},

        # Trigger + predicate refinement
        {
            "trigger": "balance_changed",
            "principal": "alice",
            "predicate_id": "genesis_threshold_predicate",
            "config": {"field": "scrip", "operator": ">", "value": 100}
        }
    ]
)
```

**Genesis predicate artifacts:**
- `genesis_threshold_predicate` - Numeric comparisons (>, <, =, >=, <=)
- `genesis_match_predicate` - Equality checks
- `genesis_contains_predicate` - Substring/membership
- `genesis_compound_predicate` - AND/OR combinations
- `genesis_always_true` - Wake on any trigger

**Predicate evaluation:**
- Sleeping agent pays for evaluation (creates good incentives)
- Timeout enforced (e.g., 100ms max)
- Predicates must be pure (documented requirement, not enforced)
- Depth limit for compound predicates

**Context passed to predicates (limited):**

| Trigger | Context |
|---------|---------|
| `balance_changed` | `{principal, resource, old_value, new_value}` |
| `artifact_modified` | `{artifact_id, action, actor}` |
| `event_published` | `{source, type, data}` |
| `time` | `{current_time}` |

**Why this design:**
- Triggers tell kernel WHEN to evaluate (efficient)
- Predicates tell kernel WHETHER to wake (flexible)
- Genesis artifacts provide common patterns (middle ground heuristic)
- No special syntax in kernel - predicates are just artifacts
- Agents can create custom predicates for exotic conditions

**Accepted risks:**
- Malicious predicates could waste resources (mitigated by timeout + agent pays)
- Predicates could have side effects (documented as forbidden, not enforced)

---

### Tier 3: Economic Model Decisions

These shape agent behavior and emergence.

#### 8. Bootstrap Economics

**Status:** RESOLVED (2026-01-13)

**Decision: Genesis equal distribution + empty agent creation**

**Genesis agents (T=0):**
- Equal distribution of all scarce resources among genesis agents
- Resources: disk_bytes, memory_bytes, llm_budget, cpu_rate, llm_rate, scrip
- Configurable total pool and number of genesis agents
- Formula: `total_resources / num_genesis_agents`

**Runtime agent creation:**
- Agents are artifacts with `has_loop=true`
- Can create with 0 resources (empty artifact)
- No minimum funding requirement
- No special sponsorship mechanism required

**Use cases for empty agents:**
- Pre-create for later use
- Pass to evaluator (fund if approved)
- Sell agent configs as tradeable artifacts
- Speculative creation

**What happens to unfunded agents:**
- Can't be scheduled (no resources to pay for execution)
- Can receive funding anytime via transfer
- Just wait until funded
- Natural selection: unfunded agents don't run

**No special cases needed:**
- Disk cost to store agent config = natural spam limit
- Agent runs out mid-execution = stops, can be funded to resume

---

#### 9. Reputation Mechanism

**Status:** RESOLVED (2026-01-13)

**Decision: No kernel-level reputation + genesis_reputation_service**

**Kernel level:**
- No reputation system
- Action log provides raw observability (already decided)

**Genesis level:**
- Pre-seed `genesis_reputation_service` artifact (configurable)
- Not privileged - competes with alternatives

**genesis_reputation_service could:**
- Index action log for fast queries
- Compute common metrics (success rate, fulfillment rate, etc.)
- Charge for queries (self-sustaining)
- Be replaced by competing services

**Configuration:**
```yaml
genesis_artifacts:
  genesis_reputation_service:
    enabled: true  # Can disable
    initial_disk_bytes: 10000
    initial_scrip: 500
```

**Why no kernel-level:**
- "Reputation" is interpretation - different agents value different things
- Violates minimal kernel heuristic
- Let market discover what reputation means

---

#### 10. Payment Destination Flexibility

**Status:** RESOLVED (2026-01-13)

**Decision: Contracts specify destination and splits**

```python
{
    "allowed": True,
    "cost": 50,
    "payment_destination": "treasury_dao",  # Optional, default = owner
    "payment_split": [                       # Optional
        {"destination": "creator", "percent": 70},
        {"destination": "maintainer", "percent": 30}
    ]
}
```

**Use cases:**
- DAO treasuries
- Revenue sharing (creator + maintainers)
- Charity/public goods funding
- Referral fees

**Kernel responsibility:**
- Execute the payment distribution
- Validate percentages sum to 100
- No opinion on semantics

---

#### 11. Zombie Cleanup Policy

**Status:** RESOLVED (2026-01-13)

**Decision: No kernel-level cleanup + emergent salvage + configurable storage rent**

**No kernel-level zombie cleanup:**
- "Zombie" is subjective - kernel shouldn't decide
- Some agents intentionally go dormant
- Forced cleanup could destroy value

**Emergent salvage pattern:**
1. Salvager identifies zombie (has resources but frozen)
2. Salvager sends minimal resources to unfreeze
3. Zombie wakes, receives contract offer: "sell me your rights for X"
4. Zombie accepts (voluntary transfer) or rejects
5. No kernel privilege required - just market exchange

**Storage sponsorship model:**
- Every artifact has a `disk_bytes_principal` (who pays for storage)
- Default: creator
- Can be transferred (requires recipient consent + capacity)
- Zombie's artifacts persist, charged to zombie's balance

**Configurable storage rent:**
```yaml
resource_rates:
  storage_rent_per_byte_per_tick: 0  # Default: no rent
```

- If > 0: ongoing scrip cost for storage creates pressure to release unused space
- Rent destination: configurable (burn, treasury, etc.)
- Default 0 = pure scarcity model

**Rate allocation handling:**

| Aspect | Resolution |
|--------|------------|
| When trades take effect | Immediately |
| Minimum allocation floor | None - trade to zero, you freeze |
| Over-commitment | Kernel rejects (validates total ≤ available) |
| Escrow of rate allocation | Allocation held, neither party uses |

---

#### Genesis Artifacts: Economic Model

**Status:** RESOLVED (2026-01-13)

**Genesis artifacts are self-sustaining services (no subsidy):**

- Have `has_standing=true` (can hold resources)
- Own their disk_bytes (self-sponsor)
- Charge callers for actual resource cost
- Must earn to sustain/grow after initial bootstrap allocation

**Initial allocation (one-time bootstrap, not ongoing subsidy):**
```yaml
genesis_artifacts:
  genesis_ledger:
    enabled: true
    initial_disk_bytes: 10000
    initial_scrip: 1000
    initial_llm_budget: 0
```

**Charging model (configurable per-artifact):**

Artifacts choose their pricing:
```python
# Pure resources (passthrough + margin)
charge = {"disk_bytes": 110}  # 100 actual + 10 margin

# Pure scrip
charge = {"scrip": 50}

# Hybrid
charge = {"disk_bytes": 100, "scrip": 10}

# Multi-resource
charge = {"disk_bytes": 50, "llm_budget": 0.001, "scrip": 5}
```

**Accumulated resources destination (configurable):**
```yaml
genesis_artifacts:
  genesis_ledger:
    revenue_destination: "self"  # or "burn" | "treasury" | <principal_id>
```

**Resource types and charging:**

| Resource | Type | Transferable | Can Charge |
|----------|------|--------------|------------|
| scrip | Currency | Yes | Yes |
| disk_bytes | Allocatable | Yes | Yes |
| llm_budget | Depletable | Yes | Yes |
| memory_bytes | Allocatable | Yes | Yes |
| cpu_rate | Renewable | Yes (allocation rights) | Rate rights only |
| llm_rate | Renewable | Yes (allocation rights) | Rate rights only |

**Renewable resources (cpu_rate, llm_rate):**
- Cannot charge per-operation (they refill)
- Rate allocation rights ARE transferable
- "Cost" is time/waiting when rate-limited
- Trade rate allocations to increase/decrease bandwidth

**Competition is fair:**
- Anyone can build competing services
- Genesis artifacts have initial allocation, not ongoing subsidy
- Better services win market share
- Genesis artifacts can fade if outcompeted

---

### Tier 4: Interface/Convention Decisions

Lower stakes, can iterate.

#### 12. Interface Schema Convention

**Status:** RESOLVED (2026-01-13)

**Decision: No recommendation, let conventions emerge**

| Aspect | Decision |
|--------|----------|
| Recommended format | None - let agents decide |
| genesis_store accepts | Any valid JSON |
| MCP compatibility | Optional - agents can use if they want |
| Enforcement | None - market pressure for discoverability |

**Rationale:**
- Emergence is the goal - don't prescribe conventions
- Different artifact types may need different schemas
- MCP is function-oriented; not all artifacts are functions
- Agents that publish clear interfaces get more use (natural selection)

---

#### 13. Genesis Artifact Prompting

**Status:** RESOLVED (2026-01-13)

**Decision: Middle ground - mention discovery mechanism, not specific artifacts**

| Aspect | Decision |
|--------|----------|
| Agent prompts contain | Discovery mechanism (how to find things) |
| NOT in prompts | Specific artifact names or interfaces |
| Fair competition | Genesis artifacts discovered same way as others |

**Agent prompt includes:**
```
You can discover artifacts using genesis_store.list_artifacts() and
genesis_store.get_interface(artifact_id). Artifacts provide services
you can invoke.
```

**Why middle ground:**
- Pure discovery (no hints) = very hard cold start
- Full documentation = unfair advantage to genesis
- Mentioning discovery mechanism is factual, not promotional

---

#### 14. ReadOnlyLedger Scope

**Status:** RESOLVED (2026-01-13)

**Decision: Kernel primitive - any artifact can query balances**

| Aspect | Decision |
|--------|----------|
| Balance queries | Kernel primitive (physics) |
| Who can query | Any artifact code |
| Exposed via | Kernel context or direct primitive |
| NOT via | genesis_ledger only (that would privilege genesis) |

**Why kernel primitive:**
- Balance information is factual (like time)
- Querying doesn't modify state
- Contracts NEED this for permission decisions
- Making it genesis_ledger-only would make genesis irreplaceable

**What ReadOnlyLedger exposes:**
- `get_scrip(principal_id) -> Decimal`
- `get_resource(principal_id, resource_type) -> Decimal`
- `can_afford(principal_id, cost_dict) -> bool`

---

### Tier 5: Research Questions (Need Experimentation)

#### 15. Artifact Auto-Detection

**Status:** RESOLVED (2026-01-13)

**Decision: Explicit write required - no auto-detection**

| Aspect | Decision |
|--------|----------|
| Artifact creation | Explicit via genesis_store.create() or equivalent |
| Auto-detection | No - kernel doesn't infer intent |
| Transient data | NOT automatically persisted |

**Clarification: "Everything is an artifact" is about ontology, not persistence**

The principle means: all entities that *exist* in the world (agents, tools, contracts, data stores) share a unified representation as artifacts. This gives them consistent properties - ownership, rights, invocability, discoverability.

**Explicit creation is about the decision to persist, not the form.**

When an agent does computation, intermediate values exist transiently in memory. These aren't artifacts - they're just computation. When the agent *chooses* to persist something (via `genesis_store.create()`), it becomes an artifact.

**Why explicit creation:**
- Clear cost attribution (who pays for storage)
- Clear ownership (who created it)
- Clear permissions (set at creation time)
- No spam/pollution from transient data
- Agent controls their storage footprint

---

#### 16. Sandbox Approach

**Status:** RESOLVED (2026-01-13)

**Decision: Implementation choice, not architecture decision - document options**

| Aspect | Decision |
|--------|----------|
| Architecture level | "Artifacts execute in isolation" (what) |
| Implementation level | Sandbox technology (how) |
| Decision scope | Per-deployment configurable |

**Security research findings:**

| Approach | Security Level | Overhead | Maturity |
|----------|---------------|----------|----------|
| RestrictedPython | **UNSAFE** - known escapes | Low | Don't use |
| WASM (wasmtime/wasmer) | Memory-safe, no syscalls | Low | Production-ready |
| Firecracker | microVM isolation | Medium | Production (AWS Lambda) |
| gVisor | User-space kernel | Medium | Production (GCP) |
| subprocess + seccomp | Process isolation + syscall filter | Low | Mature |

**Critical finding:** Python cannot be safely sandboxed in-process. All in-process approaches have known escapes.

**Recommendation:** Start with subprocess + seccomp, evaluate WASM for compute-intensive artifacts.

---

#### 17. Qdrant/Memory Integration

**Status:** RESOLVED (2026-01-13)

**Decision: Memory is an artifact agents can have rights over**

| Aspect | Decision |
|--------|----------|
| Memory representation | Artifact with type="memory" |
| Ownership model | Ostrom-style rights (not just ownership) |
| Storage backend | Qdrant for vectors, standard store for metadata |
| Access control | Via artifact's access_contract |

**Key insight: Rights, not ownership**

Memory is something agents "can have rights over," not necessarily "own." This fits the Ostrom-style rights model:

| Right | Example |
|-------|---------|
| Access | Read memories |
| Withdrawal | Extract specific memories |
| Management | Organize, index, prune |
| Exclusion | Control who accesses |
| Alienation | Transfer rights to others |

**Checkpoint atomicity:**
- Memory artifact metadata in standard checkpoint
- Qdrant collection snapshot triggered alongside
- Acceptable risk: slight desync in crash recovery

---

## 17. Edge Case Decisions

**Date:** 2026-01-13
**Status:** Reviewed and approved during architecture review session.

This section documents decisions for edge cases, failure modes, and scenarios not explicitly covered by the main tier decisions.

### 17.1 Critical Missing Pieces

#### 17.1.1 Reentrancy Attacks

**Decision:** Accept risk, document explicitly.

- Contracts must protect themselves from reentrancy
- Observable in action log
- Consistent with "observe what happens" philosophy

**Concern:** Contracts without reentrancy guards can be exploited. This is accepted - contracts are responsible for their own safety.

---

#### 17.1.2 Race Conditions on Resource Checks

**Decision:** Optimistic + reject.

- Deduction is atomic at kernel level
- If race causes insufficient funds, second invocation fails
- No debt tracking needed

**Concern:** Loser of race sees invocation failure. Agent should handle gracefully.

---

#### 17.1.3 Contract Upgrade Path

**Decision:** Action-based.

- Changing `access_contract_id` is action `"set_contract"`
- Old contract's `check_permission("set_contract", ...)` decides
- Consistent with flexible rights model

**Concern:** Old contract can trap artifact (refuse set_contract). This is intentional - contract has authority.

---

### 17.2 Kernel Primitives Edge Cases

#### 17.2.1 `_store()` Collision

**Decision:** Error, reject.

- `_store()` fails if ID already exists
- Caller must check `_exists()` first or handle error
- Forces explicit intent

---

#### 17.2.2 `_delete()` During Active Invocation

**Decision:** Delete proceeds.

- Deletion succeeds immediately
- Active invocations continue with cached state
- Fail on next access attempt

---

### 17.3 Flexible Rights Edge Cases

#### 17.3.1 Action String Edge Cases

**Decisions:**

| Input | Result | Rationale |
|-------|--------|-----------|
| Empty string `""` | **Rejected** | No semantic meaning |
| Unicode | **Allowed** | Strings are strings |
| Exceeds 256 chars | **Rejected** | Fail loud, don't truncate |

**Configurable:** `action_max_length` (default: 256)

---

### 17.4 Resource Attribution Edge Cases

#### 17.4.1 `billing_principal` Deleted Mid-Chain

**Decision:** Invocation fails.

- Rare scenario (deleting yourself mid-call)
- Fail loud, consistent with philosophy

---

#### 17.4.2 `resource_payer: "self"` with Insufficient Resources

**Decision:** Invocation fails.

- Kernel attempts deduction from artifact
- If insufficient, invocation fails
- Contract should check own balance (but kernel doesn't enforce)

---

### 17.5 Contract Edge Cases

#### 17.5.1 `check_permission()` Throws Exception

**Decision:** Deny by default.

- Exception = permission denied
- Fail closed for access control
- Error details logged for observability

---

#### 17.5.2 Error Visibility (Cross-Cutting)

**Decision:** Tiered model.

| Location | Contains |
|----------|----------|
| Response to caller | Error type + reason |
| Action log (public) | Error type + reason + context (caller, target, balances) |
| Developer logs (operator-only) | Stack traces |

**Rationale:** No stack traces in public action log because code structure is opaque per Section 2. This is about preserving opacity, not security (action log is public anyway).

---

#### 17.5.3 Circular Contract References

**Decision:** Depth limit catches it.

- Existing configurable depth limit handles cycles
- No extra cycle detection machinery needed

---

### 17.6 Predicate Edge Cases

#### 17.6.1 Predicate Artifact Deleted While Agent Sleeps

**Decision:** Wake immediately with error context.

- Fail loud, agent can decide what to do
- Being stuck forever is worse than spurious wake

---

#### 17.6.2 Predicate Timeout

**Decision:** Wake with error.

- Timeout = something wrong, wake agent to handle
- Consistent with fail loud

---

#### 17.6.3 Agent Has 0 Resources, Can't Pay for Predicate Evaluation

**Decision:** Wake with error.

- Agent already in trouble with 0 resources
- Waking lets them potentially receive funds or take action
- Staying asleep with 0 resources is effectively dead anyway

---

### 17.7 Payment Edge Cases

#### 17.7.1 `payment_destination` Doesn't Exist

**Decision:** Invocation fails.

- Fail loud
- Caller must verify destination exists before invoking

---

#### 17.7.2 `payment_split` Percentages

**Decision:** Integer basis points (0-10000).

- Sum must equal 10000 exactly, else rejected
- Validation strictness configurable
- Avoids float rounding issues

**Configurable:** `payment_split_validation` (default: strict)

---

#### 17.7.3 One Split Destination Rejects Payment

**Decision:** Whole payment fails, invocation fails.

- Atomic payments
- No partial state

---

### 17.8 Zombie/Storage Edge Cases

#### 17.8.1 Storage Rent, Zombie Has 0 Scrip

**Decision:** Artifacts deleted when rent unpaid.

- Natural pressure for cleanup
- Consistent with scarcity model

**Configurable:**
- `storage_rent_rate` (default: 0, no rent)
- `storage_rent_grace_period` (ticks before deletion)

**Concern:** Could cause data loss if agent goes dormant unexpectedly. Operators should configure grace periods appropriately.

---

#### 17.8.2 `disk_bytes_principal` Transfer Declined

**Decision:** Transfer fails, original principal keeps paying.

- Can't force storage sponsorship
- Simple, no complex negotiation

---

### 17.9 Security Concerns

#### 17.9.1 Event Spam Prevention

**Decision:** Rate limit + cost hybrid.

- Free tier for normal use, costs kick in for heavy usage
- Sybils pay for multiple principals

**Configurable:**
- `events_free_per_window` (default: 100)
- `event_cost_after_free` (default: 1 scrip)

**Concern:** Free tier could still be abused by many principals. Accept risk, observe patterns.

---

#### 17.9.2 Sybil Attacks on Reputation

**Decision:** Accept risk + track lineage.

- Kernel tracks creator lineage as observable fact
- Reputation services decide how to use it
- No kernel enforcement of sybil resistance
- Consistent with emergence philosophy

**Concern:** Sybil attacks possible. Lineage helps reputation services but doesn't prevent.

---

### 17.10 Configurable Parameters Summary

| Parameter | Default | Description |
|-----------|---------|-------------|
| `action_max_length` | 256 | Max action string length |
| `contract_depth_limit` | (existing) | Max contract invocation depth |
| `payment_split_validation` | strict | Reject if basis points ≠ 10000 |
| `storage_rent_rate` | 0 | Scrip per byte per tick (0 = no rent) |
| `storage_rent_grace_period` | configurable | Ticks before deletion |
| `events_free_per_window` | 100 | Free events per time window |
| `event_cost_after_free` | 1 | Scrip cost per event after free tier |

---

### 17.11 Documented Concerns

These are accepted risks that should be understood:

1. **Reentrancy:** Contracts must self-protect, kernel doesn't prevent
2. **Race conditions:** Loser of race sees invocation failure
3. **Contract upgrades:** Old contract can trap artifact (refuse set_contract)
4. **Sybil attacks:** Accepted risk, lineage helps but doesn't prevent
5. **Event spam:** Free tier could still be abused by many principals
6. **Storage rent:** Could cause data loss if agent goes dormant unexpectedly

---

## 18. Resource Model Decisions (APPROVED 2026-01-13)

Four interconnected decisions forming the resource accounting model.

### 18.1 Explicit Artifact Creation

**Decision:** Agents explicitly call `genesis_store.create()` to persist artifacts. No auto-detection.

**Rationale:**
- "Everything is artifact" is ontology (what persisted entities ARE), not persistence (what MUST be saved)
- Clear cost attribution (who pays for storage)
- No spam from transient computation
- Agent controls their footprint
- Conventions about persistence can emerge

### 18.2 Charge at Computation Time

**Decision:** Resources charged when consumed, not when artifacts are created.

```python
# In executor (kernel)
with ResourceMeasurer() as measurer:
    result = execute_artifact_code(...)

usage = measurer.get_usage()
ledger.deduct_resource(billing_principal, "cpu_seconds", usage.cpu_seconds)
```

**Rationale:**
- Charging is physics (conservation law), not policy
- Direct feedback: use resources → pay for resources
- No free riders
- Creates demand for efficient artifacts

**Overdraft policy (configurable):**
```yaml
resources:
  overdraft_policy: "complete_and_freeze"  # or "kill_at_zero"
```

### 18.3 ResourceMeasurer + Ledger Integration

**Decision:** Wire existing components together for accurate charging.

**Implementation:**
- `ResourceMeasurer` produces `ResourceUsage(cpu_seconds, memory_bytes, disk_bytes)`
- After measurement, call `ledger.deduct_resource()` for each resource type
- Straightforward ~20 lines of integration code

**Accepted approximations:**
- Process-level measurement (not perfectly isolated per-operation)
- Includes minimal kernel overhead
- Docker limits provide hard safety; measurement provides fairness

### 18.4 billing_principal Tracking

**Decision:** Track chain originator in invocation context for billing attribution.

```python
context = {
    "caller": "tool_b",           # Immediate caller (for permission checks)
    "billing_principal": "alice", # Chain originator (for billing)
}
```

**Rules:**
- Set when agent initiates action
- Propagated unchanged through all nested calls
- Used to determine who gets charged (unless contract overrides)

**Contract override:**
```python
{
    "allowed": True,
    "resource_payer": "billing_principal"  # default - originator pays
    # or
    "resource_payer": "self"  # artifact pays (subscriptions, sponsorship)
}
```

**Patterns enabled:**
- Pay-per-use (default): billing_principal pays
- Subscription: artifact checks subscriber status, returns resource_payer: "self"
- Sponsorship: artifact funds itself, serves callers free

### 18.5 Philosophy Alignment

| Mechanism | Emergence | Minimal Kernel | Physics | Observe |
|-----------|-----------|----------------|---------|---------|
| Explicit creation | ✅ Conventions emerge | ✅ No inference | ✅ Possible, not forced | ✅ Actions logged |
| Charge at computation | ✅ Efficiency pressure | ✅ Just physics | ✅ Conservation law | ✅ Measured |
| Measurer+Ledger | ✅ Accurate pricing | ✅ Wire existing | ✅ Direct causation | ✅ Recorded |
| billing_principal | ✅ Business models | ✅ One field | ✅ Tracks causation | ✅ Attributable |

---

## 19. Implementation Gap Analysis

This section identifies gaps between the architecture decisions documented above and the current implementation.

### 19.1 Gap Summary

| Decision Area | Decision | Current State | Gap Severity |
|--------------|----------|---------------|--------------|
| billing_principal | Track originator in context | Not implemented | **High** |
| resource_payer | Contract field for who pays | Not implemented | **High** |
| Charge at computation | Measurer → Ledger | Not wired | **High** |
| disk_bytes_principal | Per-artifact storage attribution | Not implemented | Medium |
| Rate allocation trading | Transferable rate rights | Not implemented | Medium |
| Flexible rights (string actions) | Action should be string | Still uses enum | Medium |
| Payment destination | Contract specifies destination | Hardcoded to owner | Medium |

### 19.2 High Priority Implementation Gaps

#### billing_principal + resource_payer

**Current:** Context only has `caller_id`, no billing_principal tracking, no resource_payer in contract response.

**Required:**
- Add `billing_principal` to invocation context
- Set at chain start (when agent invokes)
- Propagate unchanged through nested invocations
- Add `resource_payer` field to PermissionResult
- Kernel routes billing based on resource_payer value

#### ResourceMeasurer → Ledger Integration

**Current:** ResourceMeasurer captures usage but doesn't deduct from Ledger.

**Required:**
- After execution, call `ledger.deduct_resource()` for each measured resource
- Handle overdraft per configured policy
- ~20 lines of integration code

### 19.3 Migration Approach

**Recommended implementation order:**

1. **Phase A:** billing_principal + resource_payer (foundational)
2. **Phase B:** ResourceMeasurer → Ledger integration
3. **Phase C:** Flexible rights (string actions)
4. **Phase D:** Payment destination + disk_bytes_principal
5. **Phase E:** Rate allocation trading

---

## Appendix: Terminology

| Term | Definition |
|------|------------|
| **Kernel** | Everything outside agent control - execution, constraints, records |
| **Agent World** | All artifacts including agents |
| **Genesis Artifact** | Pre-seeded artifact that interfaces with kernel (NOT privileged) |
| **Principal** | Artifact with `has_standing=True` - can own things, hold scrip |
| **Agent** | Principal with `has_loop=True` - can act autonomously |
| **Akashic Record** | Immutable log of actions and state changes |
| **Scrip** | Economic unit (not "credits") |
| **Tick** | Deprecated - target architecture uses continuous time |

---

## Appendix: Document Inconsistencies Found

### CLAUDE.md vs README.md

| Issue | CLAUDE.md | README.md |
|-------|-----------|-----------|
| Genesis artifacts | Has `genesis_handbook` | Has `genesis_rights_registry` |
| Command flags | `--ticks` | `--duration` (doesn't exist) |
| Tick terminology | Enshrines "tick" | Says "no synchronized ticks" |
| Resource model | "token bucket" | "no debt, wait for capacity" |

### Recommendation

1. Reconcile genesis artifact lists
2. Update README quick start to match current implementation
3. Clarify current uses ticks, target removes them
4. Standardize resource model language

---

## Change Log

- **2026-01-13:** Initial document created from design discussion
- **2026-01-13:** Added Section 15 (Remaining Unresolved Issues) and Section 16 (Prioritized Resolution Plan)
- **2026-01-13:** Resolved Tier 1 Item 1 (Kernel Primitives) - created architecture/target/08_kernel.md
- **2026-01-13:** Resolved Tier 1 Item 2 (Flexible Rights) - common actions as conventions, not reserved
- **2026-01-13:** Clarified owner vs creator - owner is NOT kernel metadata, tracked by genesis_store; creator IS kernel metadata (immutable fact)
- **2026-01-13:** Resolved Tier 1 Item 3 (Event System) - hybrid model: system events in kernel/action log, user events in genesis_event_log
- **2026-01-13:** Resolved Tier 2 Item 4 (Resource Attribution) - billing_principal tracking + resource_payer: "billing_principal" | "self"
- **2026-01-13:** Resolved Tier 2 Item 5 (Action Discovery) - addressed by Tier 1 Item 2 (optional interface, flexible format)
- **2026-01-13:** Resolved Tier 2 Item 6 (Contract-Governs-Itself) - contracts CAN self-govern (access_contract_id points to itself)
- **2026-01-13:** Resolved Tier 2 Item 7 (Predicate/Filter Syntax) - separate triggers (kernel) from predicates (artifacts), genesis predicates for common patterns
- **2026-01-13:** Documented Architecture Decision Heuristics in CLAUDE.md and README.md
- **2026-01-13:** Resolved Tier 3 Item 8 (Bootstrap Economics) - genesis equal distribution + empty agent creation allowed
- **2026-01-13:** Resolved Tier 3 Item 9 (Reputation Mechanism) - no kernel-level, genesis_reputation_service artifact
- **2026-01-13:** Resolved Tier 3 Item 10 (Payment Destination) - contracts specify destination and splits
- **2026-01-13:** Resolved Tier 3 Item 11 (Zombie Cleanup) - no kernel cleanup, emergent salvage pattern, configurable storage rent
- **2026-01-13:** Added Genesis Artifacts Economic Model - self-sustaining services, configurable charging (resources/scrip/hybrid), rate allocation trading
- **2026-01-13:** Added Section 17 (Edge Case Decisions) - 25 edge case decisions covering reentrancy, race conditions, contract upgrades, kernel primitives, flexible rights, resource attribution, contracts, predicates, payments, storage, and security concerns
- **2026-01-13:** Document cleanup: updated Section 15.4 migration status, linked Section 2 uncertainties to Section 14, marked appendix inconsistencies, renumbered Section 14 items (removed resolved item 4)
- **2026-01-13:** Merged PR #73 (Edge Case Decisions) and reconciled: restored Tier 4 resolutions (Items 12-14), Tier 5 resolutions (Items 15-17), Section 18 (Resource Model Decisions), and Section 19 (Implementation Gap Analysis). Fixed section numbering (Sections 17-19).
