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

### Uncertainty

- How do agents verify artifact behavior without seeing code?
- How does reputation form without observing failures?
- Should there be an opt-in "open source" mode for artifacts?

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
| Agent | Yes | Yes (`can_execute=True`) |
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

### has_standing and can_execute Flags

These are kernel-level because kernel must know:

| Flag | Kernel Needs to Know | Why |
|------|---------------------|-----|
| `has_standing` | Can this artifact have a ledger balance? | Kernel won't create ledger entries for non-principals |
| `can_execute` | Should I schedule this for autonomous execution? | Kernel only runs agents, not passive artifacts |

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

4. **Resource attribution in nested invocations** - RESOLVED
   - See Section 7 and Tier 2 Item 4 for billing_principal + resource_payer model

### Medium Priority

5. **Should there be opt-in "open source" mode for artifacts?**
   - Visible code in exchange for reputation boost?

6. **Predicate wake conditions**
   - How evaluated efficiently?
   - What state can predicates reference?

7. **Payment destination flexibility**
   - Extend PermissionResult to include destination?
   - What about splits (50% to owner, 50% to treasury)?

8. **Artifact auto-detection vs explicit store.write()**
   - User wondered if kernel could auto-detect artifact creation
   - Permission model unclear with auto-detection

### Lower Priority

9. **MCP vs custom interface schemas**
   - Should we recommend MCP for discoverability?
   - Or let conventions emerge?

10. **Genesis artifact advantage**
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
| Current→Target migration | Broken intermediate states | No migration roadmap |
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

**Questions:**
- New agents start with 0 resources
- How do they acquire initial resources?
- Who funds them and why (incentive)?

**Options:**

| Option | Description |
|--------|-------------|
| **Genesis endowment** | System gives initial stake |
| **Sponsor model** | Existing agents fund new ones (investment) |
| **Work-first** | Agents can do limited work to earn |
| **Emergent philanthropy** | Hope someone helps (risky) |

---

#### 9. Reputation Mechanism

**Questions:**
- How does reputation form?
- Is it explicit (stored) or implicit (compute from history)?
- Tradeable? Transferable?
- Who can see it?

**Options:**

| Option | Description |
|--------|-------------|
| **Implicit from action log** | Agents compute from observable history |
| **Explicit rating system** | Agents rate each other |
| **Stake-based** | Reputation = resources at risk |
| **No system, emergent** | Let agents figure it out |

---

#### 10. Payment Destination Flexibility

**Questions:**
- Currently cost goes to owner
- Should contract be able to specify destination?
- Can payments be split?
- Can destination be a DAO/treasury?

**Proposed extension:**
```python
PermissionResult = {
    "allowed": True,
    "cost": 50,
    "payment_destination": "treasury_dao",  # Optional, defaults to owner
    "payment_split": [                       # Optional, for splits
        {"destination": "creator", "percent": 70},
        {"destination": "maintainer", "percent": 30}
    ]
}
```

---

#### 11. Zombie Cleanup Policy

**Questions:**
- When is an agent considered "zombie"?
- What happens to its resources/artifacts?
- Who can trigger cleanup?
- Is there a grace period?

**Options:**

| Option | Description |
|--------|-------------|
| **No cleanup (current)** | Zombies accumulate forever |
| **Inactivity timeout** | N ticks/time without action = zombie |
| **Balance threshold** | Can't afford to act = zombie |
| **Explicit abandon** | Agent declares itself done |
| **Salvage auction** | Others can bid on zombie assets |

---

### Tier 4: Interface/Convention Decisions

Lower stakes, can iterate.

#### 12. Interface Schema Convention

**Question:** Should we recommend a schema format for artifact interfaces?

**Options:**
- Recommend MCP for function-like interfaces
- Recommend nothing, let conventions emerge
- Define our own minimal schema

---

#### 13. Genesis Artifact Prompting

**Question:** How much do we tell agents about genesis artifacts?

**Options:**
- Full documentation in prompt (easy start, unfair)
- Just "use kernel.list_artifacts()" (fair, hard start)
- Middle ground: mention categories exist but not specifics

---

#### 14. ReadOnlyLedger Scope

**Question:** Who gets read-only ledger access?

**Options:**
- Only contract code (current)
- All artifact code
- All agents
- Available via genesis_ledger only

---

### Tier 5: Research Questions (Need Experimentation)

#### 15. Artifact Auto-Detection

**Question:** Can kernel auto-detect artifact creation instead of explicit write?

**Needs:** Prototype to understand permission/timing implications

---

#### 16. Sandbox Approach

**Question:** What's the best contract sandbox?

**Options to evaluate:**
- RestrictedPython
- WASM (wasmer-python)
- Subprocess isolation
- Firecracker microVMs

**Needs:** Security evaluation of each

---

#### 17. Qdrant/Memory Integration

**Question:** How does vector store fit the artifact model?

**Sub-questions:**
- Is memory content stored in Qdrant or artifact store?
- How are they synchronized?
- Checkpoint atomicity?

**Needs:** Design spike

---

## Appendix: Terminology

| Term | Definition |
|------|------------|
| **Kernel** | Everything outside agent control - execution, constraints, records |
| **Agent World** | All artifacts including agents |
| **Genesis Artifact** | Pre-seeded artifact that interfaces with kernel (NOT privileged) |
| **Principal** | Artifact with `has_standing=True` - can own things, hold scrip |
| **Agent** | Principal with `can_execute=True` - can act autonomously |
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
