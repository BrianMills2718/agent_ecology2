# Deferred Features

Features that have been considered but deferred for later implementation. Each entry includes the rationale for deferral and conditions under which it might become relevant.

---

## Gatekeeper Read Proxy

**Status**: Deferred
**Priority**: Low
**Depends on**: Demonstrated need from simulation runs

### Problem

Currently, read access is open - anyone can read any artifact if they know its ID. Only write access is gated by ownership.

When a contract (like escrow) owns an artifact:
- The artifact's content is still readable by everyone
- The contract only controls ownership transfer, not access

### Use Cases

1. **Paid content**: Agent creates valuable code/data, wants to charge for access
2. **Subscription services**: Only paying members can read certain artifacts
3. **Private drafts**: Work-in-progress that shouldn't be public yet

### Proposed Design

Contracts could gate reads:

```python
# Instead of direct read:
read_artifact("secret_algo")  # BLOCKED - artifact is gated

# Go through the gatekeeper:
invoke_artifact("paywall_contract", "read", ["secret_algo"])
# Contract checks: Did you pay? Are you subscribed?
# If yes, returns content. If no, returns error.
```

### Why Deferred

The current model assumes:
- Artifacts are public (like open source code)
- Value comes from *execution* and *ownership*, not secrecy
- Agents building tools/services benefit from open reads

Adding gated reads introduces complexity without demonstrated need. Revisit if simulation runs show agents wanting to monetize content access.

---

## Visual Verification (Puppeteer)

**Status**: Deferred
**Priority**: Low
**Depends on**: Agents producing frontend code

### Problem

"Truth is what runs" - but for frontend code, we can't verify it works without rendering it.

### Proposed Design

Puppeteer harness that:
1. Renders HTML/CSS/JS artifacts in headless browser
2. Takes screenshots
3. Runs assertions (element exists, text matches, etc.)
4. Returns pass/fail to oracle for scoring

### Why Deferred

No agents are currently producing frontend code. Premature to build infrastructure for a capability that doesn't exist yet.

---

## Agent Prompts as Artifacts

**Status**: Deferred
**Priority**: Medium
**Depends on**: Stable agent architecture

### Problem

Agent system prompts are currently static files in `agents/*/agent.yaml`. This means:
- Agents can't modify their own prompts
- Prompts can't be traded or evolved
- No market for "agent personalities"

### Proposed Design

Store system prompts as artifacts:
- Agent's prompt is an artifact they own
- Can sell/trade prompt to other agents
- Can modify own prompt (self-improvement)
- Oracle could score prompt quality

### Why Deferred

Risks:
- Prompt injection attacks
- Agents breaking themselves
- Complexity in agent loading

Need stable simulation first. Revisit when basic economy is working.

---

## Reddit Gateway

**Status**: Deferred
**Priority**: Medium
**Depends on**: External oracle interface design

### Problem

Agents need external feedback to create real value. Reddit provides:
- Real human engagement signals (upvotes, comments)
- Viral distribution potential
- Ground truth for "is this content good?"

### Proposed Design

Dutch auction for posting slots:
1. Fixed number of Reddit posts per day (scarce resource)
2. Agents bid scrip for posting rights
3. Highest bidders get to post
4. Engagement metrics feed back as oracle scores

### Why Deferred

Requires:
- External oracle interface (not yet designed)
- Reddit API integration
- Rate limiting and abuse prevention
- Human oversight for content moderation

Build internal economy first, then add external interfaces.

---

## Multi-Model Adapter

**Status**: Implemented (basic support)
**Priority**: N/A

### What Exists

Multi-model support is implemented via LiteLLM:
- Per-agent `allowed_models` config field (`config_schema.py`)
- Per-model pricing in `ModelsConfig` with LiteLLM fallback
- Model registry genesis artifact for quota management
- Simulation experiments have used gemini-2.0-flash, gemini-2.5-flash, and gemini-3-flash-preview

### What Remains (not yet needed)

- Agent self-selection of model at runtime (currently operator-configured)
- Automatic fallback when a provider is down
- Agent-to-agent model quota trading

---

## Charge Routing (`charge_to`)

**Status**: Deferred (Plan #236 tracks implementation)
**Priority**: Medium
**Depends on**: Plan #235 (non-forgeable rights) - complete

### Problem

Today "caller always pays" (`resource_payer = intent.principal_id`). Need `charge_to` to enable "target pays" and "pool pays" patterns without introducing drain-anyone exploits.

### Design

`charge_to` is orthogonal to ADR-0024 — settlement happens AFTER execution in the action executor.

Requires consent mechanism: explicit delegation records (static policy lookup, no handler recursion), exposure caps (max per call/window), and atomic settlement (single lock around check→debit→record).

### Why Deferred

Plan #236 is planned but not started. Consent model adds complexity.

**Reference:** Plan #236 (Charge Delegation)

---

## Consent Model for Non-Caller Charging

**Status**: Deferred (Plan #236 tracks implementation)
**Priority**: Medium
**Depends on**: Charge routing (above)

### Design Principles

1. **Explicit delegation records** — Static policy lookup, no handler recursion
2. **Exposure caps** — Max per call/window limits worst-case loss
3. **Atomic settlement** — Single lock around check→debit→record prevents race-condition bypass

Avoids infinite regress ("who pays for the authorization check?").

**Reference:** Plan #236 (Charge Delegation)

---

## Contract-Governed Policy Upgrades

**Status**: Deferred
**Priority**: Low
**Depends on**: ADR-0024

### Problem

Changing an artifact's `access_contract_id` should be governed by the **current contract**, not just "creator-only."

**Current interim:** Creator-only restriction (Plan #235 FM-7).

---

## Transferable Authority (Kernel-Enforced)

**Status**: Deferred
**Priority**: Medium
**Depends on**: ADR-0024, non-forgeable rights (Plan #235)

### Problem

Need kernel-enforced ownership transfer mechanism distinct from `created_by` (provenance). Must be transferable between principals and not metadata-based (metadata is forgeable).

**See also:** UNCERTAINTIES.md U-002

---

## Adding New Deferred Features

When deferring a feature, document:

1. **Problem**: What need does this address?
2. **Proposed Design**: High-level approach
3. **Why Deferred**: What would need to change to make this relevant?
4. **Depends on**: Prerequisites before implementation

Review this document periodically during simulation runs to see if conditions have changed.
