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

**Status**: Deferred
**Priority**: Low
**Depends on**: Need for model diversity

### Problem

Currently all agents use `gemini/gemini-3-flash-preview`. Future might want:
- Different models for different agents
- Agent choice of model (trade compute cost vs capability)
- Fallback when one provider is down

### Proposed Design

Abstract LLM interface:
```python
class LLMProvider(Protocol):
    async def complete(self, messages: list[Message]) -> Completion: ...
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float: ...
```

Config allows specifying provider per agent or globally.

### Why Deferred

Single model simplifies:
- Cost tracking
- Behavior consistency
- Debugging

Add when there's a specific need for model diversity.

---

## Adding New Deferred Features

When deferring a feature, document:

1. **Problem**: What need does this address?
2. **Proposed Design**: High-level approach
3. **Why Deferred**: What would need to change to make this relevant?
4. **Depends on**: Prerequisites before implementation

Review this document periodically during simulation runs to see if conditions have changed.
