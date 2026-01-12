# Target Execution Model

What we're building toward.

**Last verified:** 2026-01-12

**See current:** [../current/execution_model.md](../current/execution_model.md)

---

## Continuous Autonomous Loops

Agents act independently, not synchronized by ticks.

### Agent Loop

```python
async def agent_loop(agent):
    while agent.alive:
        # Check sleep conditions
        if agent.is_sleeping:
            await agent.wait_for_wake_condition()

        # Check rate limits (no debt - just wait for capacity)
        if not rate_tracker.has_capacity(agent.id, "cpu"):
            await rate_tracker.wait_for_capacity(agent.id, "cpu")
            continue

        # Act
        action = await agent.think()
        result = await agent.act(action)

        # Loop continues immediately
```

**No debt for renewable resources.** Agents don't accumulate negative balances. They simply wait until their rate window has capacity.

### Key Differences from Current

| Current | Target |
|---------|--------|
| System triggers agents | Agents self-trigger |
| All agents act each tick | Agents act at own pace |
| Fixed rate (1 action/tick) | Variable rate (resource-limited) |
| No sleeping | Agents can self-sleep |

---

## What Ticks Become

Ticks are NOT execution triggers. They become:

1. **Metrics aggregation windows** - Reporting, monitoring
2. **Flow accumulation reference** - Token bucket uses time, ticks just label it
3. **Oracle resolution schedule** - Periodic auction resolution

### Background Clock

```python
async def metrics_loop():
    while running:
        await asyncio.sleep(tick_duration)
        log_metrics(current_tick)
        current_tick += 1
```

Agents ignore this clock. They act based on their own loops.

---

## Agent Sleep

### Self-Managed

Agents own their sleep configuration. System provides primitives:

```python
# Agent can call these
await sleep(duration_seconds)
await sleep_until_event("escrow_listing")
await sleep_until(lambda: self.scrip > 100)
```

### Wake Conditions

| Type | Example |
|------|---------|
| Duration | "Sleep for 60 seconds" |
| Event | "Wake when new escrow listing" |
| Predicate | "Wake when my scrip > 100" |

### Why Sleep

- Conserve compute (not spending if not thinking)
- Wait for conditions (no polling)
- Strategic timing (act when opportunity arises)

---

## Race Conditions

### Handled by Artifacts, Not Orchestration

With autonomous loops, agents can act simultaneously. Conflicts resolved by genesis artifacts:

```
Agent A: purchase(artifact_x)  ─┐
                                 ├─> Escrow handles atomically
Agent B: purchase(artifact_x)  ─┘    One succeeds, one fails
```

### Artifact Responsibilities

| Artifact | Handles |
|----------|---------|
| genesis_ledger | Transfer atomicity, balance checks |
| genesis_escrow | Purchase race resolution |
| genesis_rights_registry | Quota enforcement |

### Agent Responsibility

Agents must handle failures gracefully:
- Check result of actions
- Retry or adjust strategy on failure
- Don't assume action will succeed

---

## Time Injection

System injects current timestamp into every LLM context:

```
Current time: 2025-01-11T14:30:00Z
```

Agents always know what time it is. Enables:
- Calculating oracle resolution schedule
- Coordinating with other agents
- Time-based strategies

---

## Implications

### Variable Agent Productivity
- Fast/efficient agents can do more
- Expensive thinkers fall into debt, slow down
- Natural differentiation emerges

### No Snapshot Consistency
- Agents see real-time state
- State may change between read and action
- Must handle stale reads

### Ledger Consistency

With concurrent async agents, ledger operations must be atomic:

```python
class Ledger:
    def __init__(self):
        self._lock = asyncio.Lock()

    async def transfer(self, from_id: str, to_id: str, amount: int, resource: str) -> bool:
        async with self._lock:
            if self.balances[from_id][resource] < amount:
                return False  # Insufficient funds
            self.balances[from_id][resource] -= amount
            self.balances[to_id][resource] += amount
            return True
```

**Consistency guarantees:**
- Single async lock serializes all ledger mutations
- No double-spending (balance checked under lock)
- Reads can happen concurrently (eventually consistent)
- All transfers are atomic (both sides update or neither)

**Worker processes and ledger:**
- Workers execute actions, but DON'T mutate ledger directly
- Workers return resource usage measurements
- Main process updates ledger (single point of mutation)

```
Worker Process              Main Process
     │                           │
     ├─ Execute action           │
     ├─ Measure CPU/memory       │
     ├─ Return (result, usage) ──┼─> Update ledger (under lock)
     │                           │
```

### Crash Recovery

Ledger backed by SQLite with transaction semantics:

```python
class Ledger:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)
        self.conn.execute("PRAGMA journal_mode=WAL")  # Write-ahead logging
        self._lock = asyncio.Lock()

    async def transfer(self, from_id: str, to_id: str, amount: int, resource: str) -> bool:
        async with self._lock:
            try:
                with self.conn:  # Transaction context
                    # Check balance
                    balance = self.conn.execute(
                        "SELECT amount FROM balances WHERE principal=? AND resource=?",
                        (from_id, resource)
                    ).fetchone()[0]

                    if balance < amount:
                        return False

                    # Update both sides atomically
                    self.conn.execute(
                        "UPDATE balances SET amount = amount - ? WHERE principal=? AND resource=?",
                        (amount, from_id, resource)
                    )
                    self.conn.execute(
                        "UPDATE balances SET amount = amount + ? WHERE principal=? AND resource=?",
                        (amount, to_id, resource)
                    )
                return True
            except Exception:
                # Transaction auto-rollbacks on exception
                return False
```

**Crash guarantees:**
- SQLite transactions are ACID
- If crash mid-transfer, transaction rolls back
- WAL mode allows concurrent reads during writes
- On restart, incomplete transactions are automatically rolled back

### Emergent Throttling
- Rate limits naturally throttle system throughput
- Expensive agents exhaust their rate window, must wait
- No hardcoded "max N agents"

---

## Migration Notes

### Breaking Changes
- `runner.run()` loop completely redesigned
- `advance_tick()` no longer triggers agents
- `asyncio.gather()` for thinking removed
- Phase 1/Phase 2 pattern removed

### Preserved
- Action types (noop, read, write, invoke)
- Genesis artifact interfaces
- Memory system
- LLM integration
