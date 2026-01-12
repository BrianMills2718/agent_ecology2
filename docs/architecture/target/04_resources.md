# Target Resource Model

What we're building toward.

**Last verified:** 2026-01-11

**See current:** [../current/resources.md](../current/resources.md)

---

## Resource Terminology

**Three resource categories:**

| Category | Behavior | Examples |
|----------|----------|----------|
| **Depletable** | Once spent, gone forever | LLM API budget ($) |
| **Allocatable** | Quota, reclaimable (delete/free) | Disk (bytes), Memory (bytes) |
| **Renewable** | Rate-limited via token bucket | CPU (CPU-seconds), LLM rate (TPM) |

**Distinct resources - do not conflate:**

> **Note:** Current implementation uses "compute" for LLM token tracking. Target terminology reserves "compute" for local CPU. See [Gap #11](../GAPS.md) for migration plan.

| Resource | Category | Unit | What it is |
|----------|----------|------|------------|
| LLM API $ | Depletable | USD | Real dollars spent on API calls |
| LLM rate limit | Renewable | tokens/min | Provider limits (TPM, RPM) |
| CPU | Renewable | CPU-seconds | Local compute capacity |
| Memory | Allocatable | bytes | Local RAM (reclaimable when freed) |
| Disk | Allocatable | bytes | Storage quota (reclaimable via delete) |
| Scrip | Currency | scrip | Internal economy, not a "resource" |

**LLM tokens ≠ CPU.** LLM tokens are API cost ($), CPU is local machine capacity.

**Quota ownership:** Initial distribution is configurable. Quotas are tradeable like any other asset.

---

## Renewable Resources: Token Bucket

### Rolling Window (NOT Discrete Refresh)

Rate-limited resources replenish continuously. No "tick reset" moments.

```python
class TokenBucket:
    rate: float      # Tokens per second
    capacity: float  # Max tokens
    balance: float   # Current tokens
    last_update: float

    def available(self) -> float:
        elapsed = now() - self.last_update
        self.balance = min(self.capacity, self.balance + elapsed * self.rate)
        self.last_update = now()
        return self.balance

    def spend(self, amount: float) -> bool:
        if self.available() >= amount:
            self.balance -= amount
            return True
        self.balance -= amount  # Go into debt
        return False
```

### Why Not Discrete Refresh

| Discrete (Current) | Rolling (Target) |
|--------------------|------------------|
| "Spend before reset" pressure | No artificial urgency |
| Wasteful end-of-tick spending | Smooth resource usage |
| Gaming reset boundaries | No boundaries to game |

### Examples

```
Rate = 10 tokens/sec, Capacity = 100

T=0:  balance = 100
T=5:  spend 60 → balance = 40
T=10: balance = min(100, 40 + 5*10) = 90
T=12: spend 100 → balance = -10 (debt!)
T=15: balance = -10 + 3*10 = 20 (recovering)
```

---

## Debt Model

### Compute Debt Allowed

Unlike current system, agents CAN go into debt for compute:

- Negative balance = cannot initiate new actions
- Accumulation continues in background
- Must wait until balance >= 0 to act again

### Natural Throttling

```
Agent spends 150 compute (has 100):
  → balance = -50
  → Cannot act
  → Accumulates at 10/sec
  → After 5 seconds: balance = 0
  → Can act again
```

Expensive operations → debt → forced wait → fewer concurrent actions.

### Scrip Debt = Contracts (NOT Negative Balance)

Scrip balance stays >= 0. Debt is handled differently:

```
Agent A borrows 50 scrip from Agent B:
  1. B transfers 50 scrip to A
  2. Debt artifact created: "A owes B 50 scrip"
  3. B owns the debt artifact (tradeable claim)
  4. A's scrip balance never goes negative
```

Like M1 vs M2 money - debt instruments are separate from base currency.

---

## Depletable and Allocatable Resources

| Resource | Category | Behavior | Measurement |
|----------|----------|----------|-------------|
| LLM Budget | Depletable | System-wide $, stops all when exhausted | Tokens × price from API |
| Disk | Allocatable | Quota decreases on write, reclaimable via delete | Bytes written/deleted |
| Memory | Allocatable | Per-agent tracking, reclaimable when freed | Peak bytes per action (tracemalloc) |

### Docker as Real Constraint

Stock resources map to container limits:

```bash
docker run --memory=4g --cpus=2 agent-ecology
```

These ARE the constraints. Not abstract numbers.

### Per-Agent Memory Tracking

Memory is tracked per-agent using Python's `tracemalloc`:

```python
import tracemalloc

def execute_action(agent_id: str, action: Action) -> Result:
    tracemalloc.start()
    try:
        result = execute(action)
    finally:
        current, peak = tracemalloc.get_traced_memory()
        tracemalloc.stop()

    # Charge agent for peak memory used during this action
    memory_bytes = peak
    ledger.deduct(agent_id, "memory", memory_bytes)

    return result
```

**Why tracemalloc:**
- Built into Python (no dependencies)
- Measures delta per action (fair attribution)
- Low overhead
- Works within single process (no subprocess needed)

**Tracking model:**

Memory tracked in bytes (natural unit). No conversion to "compute units".

```
Agent action uses 52,428,800 bytes (50MB) peak memory
→ ledger.track(agent_id, "memory_bytes", 52428800)
→ Per-agent memory usage visible in metrics
→ Docker --memory limit enforces actual constraint
```

---

## External Resources

All external resources (LLM APIs, web search, external APIs) follow the same pattern.

### Unified Model

| Resource | Type | Constraints |
|----------|------|-------------|
| LLM API | Flow + Stock | Rate limit (TPM) + Budget ($) |
| Web search | Flow + Stock | Queries/min + Budget ($) |
| External APIs | Varies | Per-API limits + Budget ($) |

### Core Principle

**No artificial limitations.** LLM API calls are just like any other API call. Any artifact can make them as long as resource costs are accounted for.

### Config Structure

```yaml
resources:
  external_apis:
    llm:
      provider: gemini
      tokens_per_minute: 100000
      budget_usd: 10.00
      input_cost_per_1k: 0.003
      output_cost_per_1k: 0.015

    web_search:
      provider: google
      queries_per_minute: 60
      budget_usd: 5.00
      cost_per_query: 0.01

    github:
      requests_per_minute: 100
      budget_usd: 0  # Free tier
```

### Any Artifact Can Make External Calls

```python
def run(self, args):
    # Any executable artifact can do this
    llm_result = call_llm(prompt="...", model="gemini-2.0-flash")
    search_result = call_web_search("query...")
    api_result = call_external_api("https://...")
    return process(llm_result, search_result, api_result)
```

### Who Pays

- If invoked by an agent → invoking agent pays
- If artifact has standing and acts autonomously → artifact pays from its balance

### Implementation Pattern

Artifacts wrap external services:

```python
{
    "id": "genesis_web_search",
    "can_execute": true,
    "has_standing": false,  # Tool - invoker pays
    "interface": {
        "tools": [{
            "name": "search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"}
                }
            }
        }]
    }
}
```

### Genesis vs Agent-Created

- Genesis provides working defaults (`genesis_llm`, `genesis_web_search`)
- Agents can create alternatives with different providers
- No privileged access - genesis just bootstraps useful tools

---

## System-Wide Throttling

### Flow Rate IS The Throttle

```
Rate = 10 tokens/sec per agent
5 agents = 50 tokens/sec max system throughput
Configure rate so 50 tokens/sec = sustainable for container
```

### No Hardcoded Agent Limits

- Don't limit "max N agents per tick"
- Let flow rate naturally limit throughput
- Agents in debt skip actions (fewer concurrent)

---

## Transfers

### Unilateral (Sender's Right)

You can transfer YOUR assets without recipient consent:

```python
# Agent A can do this without Agent B's permission
transfer(from=A, to=B, amount=50, resource="compute")
```

Enables:
- Vulture capitalists rescuing frozen agents
- Gifts, subsidies, strategic resource sharing

### What Can Be Transferred

| Resource | Transferable? |
|----------|---------------|
| Scrip | Yes |
| Compute quota | Yes (TBD) |
| Disk quota | Yes (TBD) |
| Debt artifacts | Yes (tradeable) |

---

## System vs Per-Agent Rate Limits

Two distinct rate limiting mechanisms operate independently.

### Per-Agent Token Bucket

Controls agent scheduling fairness:

| Setting | Purpose |
|---------|---------|
| `rate` | Tokens accumulating per second |
| `capacity` | Maximum tokens storable |

Each agent has their own bucket. Limits how often each agent can act.

### System-Wide API Rate Limit

Reflects external provider constraints:

| Setting | Purpose |
|---------|---------|
| `tokens_per_minute` | Provider's TPM limit |
| `requests_per_minute` | Provider's RPM limit (future) |

Shared across all agents. When exhausted, all agents blocked from that API.

### How They Interact

```
Agent A wants to call LLM:
  1. Check A's token bucket → has capacity? → proceed
  2. Check system API rate limit → under limit? → proceed
  3. Make API call
  4. Deduct from both: A's bucket AND system rate tracker
```

If system rate limit exhausted but agent has bucket capacity:
- Agent blocked from API
- Agent can do other work (non-API actions)
- Rate limit recovers over time

---

## Invocation Cost Model

### Who Pays for What

Payment follows the `has_standing` property:

| Artifact Type | has_standing | Who Pays |
|---------------|--------------|----------|
| Agent | true | Agent pays its own costs |
| Account/Treasury | true | Account pays its own costs |
| Tool | false | Invoker pays |
| Data | false | N/A (not executable) |

### Nested Invocation Example

```
Agent A invokes Tool B → A pays for B
  B invokes Agent C → C pays for C
    C invokes Tool D → C pays for D
```

`has_standing` = "I bear my own costs"
No standing = "Caller pays"

### Permission Check Cost

Requester pays for permission checks. Every action involves:
1. Permission check (invoke access contract) → requester pays
2. Action execution → follows standing rules above

---

## Migration Notes

### Breaking Changes
- `advance_tick()` no longer resets flow resources
- `ledger.set_resource()` replaced with token bucket
- Negative compute balances allowed
- New debt artifact type for scrip borrowing

### Preserved
- Stock resource behavior (disk)
- Scrip transfer mechanics
- Genesis artifact cost model
- Thinking cost calculation (input/output tokens)

### New Components
- TokenBucket class
- Debt artifact type
- Docker integration for limits
