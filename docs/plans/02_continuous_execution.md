# Gap 2: Continuous Agent Execution

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** #1 Rate Allocation (Complete)
**Blocks:** #21 Testing for Continuous

---

## Gap

### Current
- Tick-synchronized execution
- Runner controls when agents think
- Two-phase commit: observe parallel, execute sequential
- All agents act exactly once per tick

### Target
- Agents run continuous autonomous loops
- Agents decide when to act
- Race conditions handled by artifacts
- Ticks become metrics windows only

---

## Changes

### Files to Modify

| File | Change |
|------|--------|
| `src/simulation/runner.py` | Complete refactor of run loop |
| `src/agents/agent.py` | Add autonomous `run()` loop |
| `src/world/world.py` | Add time injection, remove tick-as-execution |
| `config/config.yaml` | Add metrics_interval, remove tick-based settings |

### Files to Keep
- Genesis artifacts (unchanged interface)
- Action types (unchanged)
- Memory system (unchanged)

---

## New Agent Loop

```python
# src/agents/agent.py

class Agent:
    async def run(self) -> None:
        """Autonomous agent loop."""
        while self.alive:
            # Check sleep
            if self._sleeping:
                await self._wait_for_wake()

            # Check debt
            if self.token_bucket.is_in_debt():
                await self._wait_for_accumulation()
                continue

            # Get current state (no snapshot, real-time)
            world_state = self.world.get_state_for_agent(self.agent_id)

            # Think
            try:
                action = await self.think(world_state)
            except InsufficientCompute:
                continue

            # Act
            result = await self.world.execute_action(action)
            self._record_result(result)

            # Optional self-delay
            if self.config.get("think_delay", 0) > 0:
                await asyncio.sleep(self.config["think_delay"])
```

---

## New Runner Structure

```python
# src/simulation/runner.py

class SimulationRunner:
    async def run(self) -> None:
        """Start all agent loops and metrics."""
        # Start agent loops
        agent_tasks = [
            asyncio.create_task(agent.run())
            for agent in self.agents
        ]

        # Start metrics loop
        metrics_task = asyncio.create_task(self._metrics_loop())

        # Start oracle loop (time-based resolution)
        oracle_task = asyncio.create_task(self._oracle_loop())

        # Wait for shutdown
        await self._wait_for_shutdown()

        # Cancel all
        for task in agent_tasks:
            task.cancel()
        metrics_task.cancel()
        oracle_task.cancel()

    async def _metrics_loop(self) -> None:
        """Background metrics aggregation."""
        while True:
            await asyncio.sleep(self.metrics_interval)
            self._log_metrics()

    async def _oracle_loop(self) -> None:
        """Background oracle resolution."""
        while True:
            await asyncio.sleep(self.oracle_interval)
            await self.oracle.resolve()
```

---

## Time Injection

```python
# src/world/world.py

def get_state_for_agent(self, agent_id: str) -> dict:
    """Get current world state with time injection."""
    return {
        "current_time": datetime.now(UTC).isoformat(),
        "balances": self.ledger.get_balances(agent_id),
        "artifacts": self.get_artifact_summaries(),
        "quotas": self.rights_registry.get_all_quotas(agent_id),
        # ... etc
    }
```

---

## Config Changes

### Current
```yaml
world:
  max_ticks: 100

llm:
  rate_limit_delay: 15
```

### Target
```yaml
world:
  max_runtime_seconds: 3600  # 1 hour max
  metrics_interval: 60       # Log metrics every 60s

oracle:
  resolution_interval: 300   # Resolve every 5 minutes
```

---

## Steps

### Step 1: Implement token bucket (prerequisite)
- See [token_bucket.md](token_bucket.md)

### Step 2: Add agent run() loop
- New `async def run()` method
- Sleep/wake primitives
- Debt checking

### Step 3: Refactor runner
- Remove tick loop
- Add agent task management
- Add metrics/oracle loops

### Step 4: Update world state
- Add time injection
- Remove snapshot-for-tick logic
- Real-time state access

### Step 5: Update config
- Time-based intervals
- Remove tick-based settings

### Step 6: Update tests
- New tests for continuous execution
- Update existing tests

---

## Verification

### Unit Tests
- Agent loop starts and stops
- Sleep/wake mechanics
- Debt blocking

### Integration Tests
- Multiple agents running concurrently
- Race conditions handled by artifacts
- Oracle resolves on schedule

### Manual Test
```bash
# Run for 60 seconds with continuous agents
python run.py --runtime 60 --agents 3
# Observe agents acting at different rates
```

---

## Rollback

Significant change. Rollback requires:
1. Revert runner.py to tick-based
2. Revert agent.py to passive
3. Revert config

Consider feature flag for gradual rollout.

---

## Risk Assessment

### High Risk
- Complete execution model change
- Many interacting components
- Race conditions more likely

### Mitigation
- Implement token bucket first (isolated)
- Add comprehensive logging
- Test with single agent first
- Gradual increase in agent count
