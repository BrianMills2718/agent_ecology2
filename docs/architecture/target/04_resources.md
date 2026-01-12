# Target Resource Model

What we're building toward.

**Last verified:** 2026-01-12

**See current:** [../current/resources.md](../current/resources.md)

---

## Resource Terminology

**Three resource categories:**

| Category | Behavior | Examples |
|----------|----------|----------|
| **Depletable** | Once spent, gone forever | LLM API budget ($) |
| **Allocatable** | Quota, reclaimable (delete/free) | Disk (bytes), Memory (bytes) |
| **Renewable** | Rate-limited via rolling window | CPU (CPU-seconds), LLM rate (TPM) |

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

## Renewable Resources: Rate Allocation

### Strict Allocation Model

Each agent gets an allocated rate. Unused capacity is wasted (not borrowable by others).

**Why strict (not work-conserving):**
- Simple to implement and reason about
- Strong incentive to trade unused allocation
- Predictable resource usage

### No Burst

Renewable resources enforce rate only, no burst capacity:
- You get X units per time period
- Use it or lose it
- No "saving up" for later

**Why no burst:**
- LLM providers enforce rolling windows anyway (can't save up)
- Creates stronger trade incentive
- Simpler model

### Rate Tracking

```python
@dataclass
class RateTracker:
    rate: float           # Units per minute (allocated)
    window_seconds: int   # Rolling window size (e.g., 60)
    usage_log: list       # (timestamp, amount) entries

    def usage_in_window(self) -> float:
        cutoff = now() - self.window_seconds
        return sum(amt for ts, amt in self.usage_log if ts > cutoff)

    def can_use(self, amount: float) -> bool:
        return self.usage_in_window() + amount <= self.rate

    def use(self, amount: float) -> bool:
        if not self.can_use(amount):
            return False  # Blocked until window rolls
        self.usage_log.append((now(), amount))
        self._prune_old_entries()
        return True
```

### Shared Resource Allocation (LLM Rate)

Provider limit is partitioned across agents:

```yaml
resources:
  llm_rate:
    provider_limit: 100000  # TPM from provider
    allocation_mode: strict
    initial_allocation:
      agent_a: 50000
      agent_b: 30000
      agent_c: 20000
      # Total = 100000 (must equal provider_limit)
```

**Rules:**
- Sum of allocations must equal provider limit
- Unallocated rate is wasted (no one can use it)
- New agents start with 0, must acquire via trade

### Trading Rate Allocation

Rate allocation stored in ledger, traded like any asset:

```python
# Agent B sells 10,000 TPM to Agent A for 100 scrip
genesis_ledger.transfer("agent_b", "agent_a", 10000, "llm_rate")
genesis_ledger.transfer("agent_a", "agent_b", 100, "scrip")
```

### Rate Enforcement

Rate limits are checked before action execution:

```python
async def run_action(agent_id: str, action: Action) -> Result:
    # Estimate resource cost
    estimated_cost = estimate_cost(action)

    # Check rate limits
    if not rate_tracker.can_use(agent_id, "llm_rate", estimated_cost.llm_tokens):
        # Queue the action, agent waits
        await rate_tracker.wait_for_capacity(agent_id, "llm_rate", estimated_cost.llm_tokens)

    if not rate_tracker.can_use(agent_id, "cpu", estimated_cost.cpu_seconds):
        await rate_tracker.wait_for_capacity(agent_id, "cpu", estimated_cost.cpu_seconds)

    # Execute and measure actual usage
    result, actual_usage = await execute_action(agent_id, action)

    # Record actual usage (may differ from estimate)
    rate_tracker.record_usage(agent_id, "llm_rate", actual_usage.llm_tokens)
    rate_tracker.record_usage(agent_id, "cpu", actual_usage.cpu_seconds)

    return result
```

**Enforcement points:**
- **Pre-execution:** Check if agent has capacity, queue if not
- **Post-execution:** Record actual usage for rate window
- **Over-limit:** Agent's next action waits until window rolls

**No penalty for estimation errors:** We estimate before, measure after. Actual usage is what counts for the rate window.

### Per-Agent Resources (CPU)

CPU doesn't have a shared provider limit. Each agent's rate is independent:

```yaml
resources:
  cpu:
    initial_allocation:
      agent_a: 0.5   # CPU-seconds per wall-clock second
      agent_b: 0.5
      # No provider limit - Docker enforces container total
```

Agents can trade CPU allocation rights.

**Measurement:** See [Per-Agent CPU Tracking](#per-agent-cpu-tracking) for how CPU-seconds are measured accurately using worker pool + `resource.getrusage()`.

---

## Debt Model

### Renewable Resources: No Debt

For rate-limited resources (LLM rate, CPU), there's no debt concept:
- If you exceed your rate, you're blocked until window rolls
- No negative balance, just "wait until you have capacity"

### Allocatable Resources: No Debt

For disk and memory:
- If you exceed quota, operation fails
- No borrowing against future - just hard limit

### Scrip Debt = Contracts (NOT Negative Balance)

Scrip balance stays >= 0. Debt is handled via debt artifacts:

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

### Per-Agent CPU and Memory Tracking

CPU and memory measurement requires capturing ALL resource usage in worker processes, including multi-threaded libraries (PyTorch, NumPy).

**Solution: ProcessPoolExecutor with asyncio**

```python
import asyncio
import resource
import tracemalloc
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass

@dataclass
class ResourceUsage:
    cpu_seconds: float
    memory_bytes: int

def execute_in_worker(action: Action) -> tuple[Result, ResourceUsage]:
    """Runs in worker process. Measures ALL resources used."""
    # Memory tracking (in worker process)
    tracemalloc.start()

    # CPU tracking
    before = resource.getrusage(resource.RUSAGE_SELF)

    result = execute(action)

    after = resource.getrusage(resource.RUSAGE_SELF)
    _, peak_memory = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    cpu_seconds = (after.ru_utime - before.ru_utime) +
                  (after.ru_stime - before.ru_stime)

    return result, ResourceUsage(cpu_seconds, peak_memory)

# ProcessPoolExecutor works with asyncio (not multiprocessing.Pool)
executor = ProcessPoolExecutor(max_workers=8)

async def run_action(agent_id: str, action: Action) -> Result:
    """Non-blocking action execution with resource tracking."""
    loop = asyncio.get_event_loop()

    # Run in worker process, non-blocking
    result, usage = await loop.run_in_executor(
        executor, execute_in_worker, action
    )

    # Deduct measured resources
    ledger.deduct(agent_id, "cpu_seconds", usage.cpu_seconds)
    ledger.deduct(agent_id, "memory_bytes", usage.memory_bytes)

    return result
```

**Why ProcessPoolExecutor (not multiprocessing.Pool):**
- Works with asyncio event loop (non-blocking)
- Multiple agents can have actions in flight concurrently
- `pool.apply()` blocks; `run_in_executor()` awaits

**Why measure in worker:**
- `tracemalloc` only sees memory in its own process
- `getrusage(RUSAGE_SELF)` only sees CPU in its own process
- Worker isolation = accurate per-action measurement

**Scalability:**

| Agents | Worker processes | Memory overhead |
|--------|------------------|-----------------|
| 10 | 8 | 400MB |
| 100 | 8 | 400MB |
| 1000 | 8-16 | 400-800MB |

Pool size is independent of agent count. Agents queue for workers.

**Pool sizing guidance:**

```yaml
# config.yaml
resources:
  worker_pool:
    max_workers: null  # null = os.cpu_count() (default)
    # Or set explicitly:
    # max_workers: 8
```

```python
import os

def get_pool_size(config: dict) -> int:
    configured = config.get("resources", {}).get("worker_pool", {}).get("max_workers")
    if configured is not None:
        return configured
    return os.cpu_count() or 4  # Fallback to 4 if cpu_count() returns None
```

**Rules of thumb:**
- CPU-bound work: `max_workers = cpu_count()`
- Mixed I/O and CPU: `max_workers = cpu_count() * 2`
- Memory-constrained: Reduce workers (each uses ~50MB)

**What's captured:**

| Activity | Measured? |
|----------|-----------|
| Python code | ✅ |
| Multi-threaded libraries (PyTorch CPU, NumPy) | ✅ |
| Any spawned threads | ✅ |
| Memory allocations | ✅ |
| I/O wait | ❌ (correctly not charged) |
| GPU compute | ❌ (separate resource) |

### Action Serialization

Actions must be picklable to send to worker processes.

**Actions are pure data:**

```python
@dataclass
class Action:
    action_type: str           # "invoke", "transfer", "create", etc.
    target_id: str             # Artifact/agent ID
    method: str                # Method name
    args: dict[str, Any]       # JSON-serializable arguments

    # NOT allowed:
    # - Lambda functions
    # - Open file handles
    # - Database connections
    # - Closures capturing local state
```

If an action needs complex state, reference it by ID and let the worker load it.

### Worker Execution Environment

Workers are separate processes. They cannot directly access the main process's world state.

**Worker receives:**
- Action data (picklable)
- Read-only snapshot of relevant artifacts

**Worker does NOT have:**
- Direct ledger access (main process updates ledger)
- Write access to artifact store
- Access to other agents' state

**How workers access artifacts:**

```python
def execute_in_worker(action: Action, artifact_snapshot: dict) -> tuple[Result, ResourceUsage]:
    """
    Worker receives:
    - action: The action to execute
    - artifact_snapshot: Read-only copy of artifacts needed for this action
    """
    # Worker can read from snapshot
    artifact = artifact_snapshot[action.target_id]

    # Execute the action
    result = artifact.execute(action.method, action.args)

    # Measure resources
    return result, measure_usage()
```

**Main process orchestrates:**

```python
async def run_action(agent_id: str, action: Action) -> Result:
    # 1. Gather artifacts needed for action
    snapshot = gather_artifact_snapshot(action)

    # 2. Send to worker with snapshot
    result, usage = await loop.run_in_executor(
        executor, execute_in_worker, action, snapshot
    )

    # 3. Main process updates ledger (not worker)
    ledger.deduct(agent_id, "cpu_seconds", usage.cpu_seconds)

    # 4. If action creates/modifies artifacts, apply to world
    apply_mutations(result.mutations)

    return result.value
```

**Key principle:** Workers compute, main process mutates world state.

---

## Local LLM Support

The system supports both API-based and local LLM models.

### API-Based LLMs (Default)

- Bottleneck: Rate limit (TPM), budget ($)
- Measurement: Tokens from API response
- Mostly I/O wait, minimal CPU

### Local CPU LLMs (llama.cpp, etc.)

Worker pool + `getrusage()` captures local LLM inference automatically:

```python
def agent_action():
    # llama.cpp runs in worker process
    # ALL CPU threads captured by getrusage()
    response = llama_generate("prompt...")
    return parse(response)
```

No special handling needed - CPU measurement includes inference.

### Local GPU LLMs (vLLM, TGI, Ollama)

GPU-based models require a model server pattern:

```
┌─────────────────────────────────────────────┐
│  Model Server (vLLM, TGI, Ollama)           │
│  - Loads model weights once (7B = 14GB)     │
│  - Handles request batching                 │
│  - Reports GPU-seconds per request          │
└─────────────────────────────────────────────┘
              ↑ Local HTTP/gRPC
              ↓
┌─────────────────────────────────────────────┐
│  Worker Pool                                │
│  - Calls model server (like API)            │
│  - getrusage() captures non-LLM CPU work    │
└─────────────────────────────────────────────┘
```

**Why model server:**
- Model weights too large to load per-worker
- Efficient batching for throughput
- GPU scheduling handled centrally

**GPU as separate resource:**

```yaml
resources:
  gpu:
    initial_allocation:
      agent_a: 0.5   # GPU-seconds per wall-clock second
      agent_b: 0.5
```

Tracked via `nvidia-smi` or `pynvml`. Traded like CPU allocation.

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

All quotas are tradeable (consistent with economic design):

| Resource | Transferable? |
|----------|---------------|
| Scrip | Yes |
| CPU rate allocation | Yes |
| LLM rate allocation | Yes |
| Disk quota | Yes |
| Memory quota | Yes |
| Debt artifacts | Yes |

Transfers via `genesis_ledger.transfer(from, to, amount, resource_type)`.

---

## System vs Per-Agent Rate Limits

Two distinct rate limiting mechanisms operate independently.

### Per-Agent Rate Allocation

Controls agent scheduling fairness:

| Setting | Purpose |
|---------|---------|
| `rate` | Units per minute allocated to this agent |

Each agent has their own allocation. Limits how often each agent can act.

### System-Wide API Rate Limit

Reflects external provider constraints:

| Setting | Purpose |
|---------|---------|
| `tokens_per_minute` | Provider's TPM limit |
| `requests_per_minute` | Provider's RPM limit (future) |

Shared across all agents. Sum of per-agent allocations equals provider limit.

### How They Interact

```
Agent A wants to call LLM:
  1. Check A's rate allocation → has capacity in window? → proceed
  2. Check system total → under provider limit? → proceed
  3. Make API call
  4. Record usage in both: A's window AND system tracker
```

If agent exceeds their allocation:
- Agent blocked from that resource
- Agent can do other work (non-rate-limited actions)
- Rolling window recovers over time

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
- `advance_tick()` no longer resets renewable resources
- `ledger.set_resource()` replaced with rate tracker
- No debt for renewable resources (wait for capacity instead)
- Scrip debt via contract artifacts (not negative balance)

### Preserved
- Allocatable resource behavior (disk)
- Scrip transfer mechanics
- Genesis artifact cost model
- Thinking cost calculation (input/output tokens)

### New Components
- RateTracker class (rolling window)
- ProcessPoolExecutor for action execution
- Docker integration for real limits
