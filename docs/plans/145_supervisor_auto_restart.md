# Plan 145: Supervisor Auto-Restart

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** None
**Blocks:** Robust long-running simulations

---

## Overview

Currently, when an agent loop crashes (runtime error in reflex, workflow, or LLM integration), it:
1. Increments an error counter
2. After N errors, pauses the agent
3. **Agent stays paused forever** (no recovery)

This leads to "Dumb Death" - agents die from bugs, not from economic failure. We want agents to survive coding errors so failure is driven by economic/predictive inadequacy.

We introduce a **Supervisor** that monitors agent loops and automatically restarts crashed agents with exponential backoff.

---

## Design

### 1. Death Types

| Death Type | Cause | Should Restart? |
|------------|-------|-----------------|
| **Dumb Death** | Runtime error, timeout, crash | ✅ Yes |
| **Smart Death** | Zero scrip, economic failure | ❌ No |
| **Voluntary Death** | Agent calls "shutdown" action | ❌ No |

### 2. Supervisor Responsibilities

```
Supervisor Loop:
├─ 1. Monitor all agent loop states
├─ 2. Detect paused/crashed agents
├─ 3. Check restart eligibility:
│     ├─ Has scrip? (not smart death)
│     ├─ Not voluntarily shutdown?
│     └─ Not exceeded max restarts?
├─ 4. If eligible, schedule restart with backoff
├─ 5. On restart:
│     ├─ Preserve agent state (memory, scrip)
│     ├─ Reset error counters
│     └─ Create new loop
└─ 6. Log all supervisor actions
```

### 3. Restart Policy

```python
@dataclass
class RestartPolicy:
    enabled: bool = True
    max_restarts: int = 10  # Per hour
    initial_backoff_seconds: float = 5.0
    max_backoff_seconds: float = 300.0  # 5 minutes
    backoff_multiplier: float = 2.0

    # Conditions
    restart_on_error: bool = True  # Runtime errors
    restart_on_timeout: bool = True  # Loop timeouts
    restart_on_resource_exhaustion: bool = False  # Wait for resources instead
```

### 4. Supervisor State

```python
@dataclass
class SupervisorState:
    agent_restart_counts: dict[str, int]  # Per hour
    agent_last_restart: dict[str, datetime]
    agent_current_backoff: dict[str, float]
    total_restarts: int
    total_permanent_deaths: int
```

### 5. Integration with Loop Manager

```python
# In agent_loop.py or new supervisor.py

class AgentSupervisor:
    def __init__(self, loop_manager: AgentLoopManager, policy: RestartPolicy):
        self.loop_manager = loop_manager
        self.policy = policy
        self.state = SupervisorState()

    async def monitor(self):
        """Continuous monitoring loop."""
        while True:
            for agent_id, loop in self.loop_manager.loops.items():
                if self._needs_restart(agent_id, loop):
                    await self._restart_agent(agent_id)
            await asyncio.sleep(1.0)

    def _needs_restart(self, agent_id: str, loop: AgentLoop) -> bool:
        # Check if loop is dead but agent should live
        if not loop.is_paused:
            return False
        if self._is_smart_death(agent_id):
            return False
        if self._exceeded_restart_limit(agent_id):
            return False
        if not self._backoff_expired(agent_id):
            return False
        return True

    async def _restart_agent(self, agent_id: str):
        # Calculate backoff
        backoff = self._get_backoff(agent_id)
        await asyncio.sleep(backoff)

        # Preserve state, create new loop
        agent = self._get_agent(agent_id)
        new_loop = self.loop_manager.create_loop(agent)

        # Update supervisor state
        self.state.agent_restart_counts[agent_id] += 1
        self.state.agent_last_restart[agent_id] = datetime.now()
        self.state.agent_current_backoff[agent_id] = min(
            backoff * self.policy.backoff_multiplier,
            self.policy.max_backoff_seconds
        )

        # Log restart
        logger.info(f"Supervisor restarted agent {agent_id} (attempt {self.state.agent_restart_counts[agent_id]})")
```

### 6. Smart Death Detection

```python
def _is_smart_death(self, agent_id: str) -> bool:
    """Check if agent died from economic failure (not a bug)."""
    # Zero scrip = economic death, don't restart
    scrip = self.world.ledger.get_scrip(agent_id)
    if scrip <= 0:
        return True

    # Voluntary shutdown
    if self._agent_requested_shutdown(agent_id):
        return True

    return False
```

---

## Implementation

### Phase 1: Supervisor Core

1. **Create supervisor module** (`supervisor.py`)
   - `AgentSupervisor` class
   - `RestartPolicy` dataclass
   - `SupervisorState` tracking

2. **Add restart detection** (`agent_loop.py`)
   - Expose `crash_reason` when loop fails
   - Distinguish error types (runtime, timeout, resource)

3. **Integrate with runner** (`runner.py`)
   - Create supervisor in `SimulationRunner.__init__`
   - Start supervisor monitoring alongside agent loops

### Phase 2: Restart Logic

4. **Implement restart method**
   - Preserve agent state (memory artifact, scrip)
   - Reset loop error counters
   - Create fresh loop instance

5. **Add backoff calculation**
   - Exponential backoff with jitter
   - Reset backoff on successful iteration

6. **Add restart limits**
   - Per-agent hourly limit
   - Total simulation restart limit

### Phase 3: Observability

7. **Add supervisor metrics**
   - Restarts per agent
   - Restart reasons
   - Time to recovery

8. **Dashboard integration**
   - Show supervisor status
   - Highlight frequently restarting agents

9. **Event logging**
   - Log all supervisor actions
   - Include crash stack traces

---

## Files Affected

| File | Change |
|------|--------|
| `src/simulation/supervisor.py` | NEW - Supervisor implementation |
| `src/simulation/agent_loop.py` | Expose crash reason |
| `src/simulation/runner.py` | Integrate supervisor |
| `config/schema.yaml` | Restart policy config |
| `src/dashboard/parser.py` | Parse supervisor events |
| `src/dashboard/server.py` | Supervisor API endpoints |

---

## Required Tests

| Test | Description |
|------|-------------|
| `test_supervisor_detects_crashed_agent` | Supervisor sees paused loops |
| `test_supervisor_restarts_dumb_death` | Runtime error triggers restart |
| `test_supervisor_no_restart_smart_death` | Zero scrip = no restart |
| `test_supervisor_backoff_increases` | Exponential backoff works |
| `test_supervisor_max_restarts` | Limit enforced per hour |
| `test_restart_preserves_state` | Memory/scrip preserved |
| `test_restart_resets_errors` | Error counter reset |

---

## Success Criteria

| Criterion | Measurement |
|-----------|-------------|
| Dumb deaths recovered | Crashed agents restart |
| Smart deaths respected | Zero-scrip agents stay dead |
| Backoff prevents thrashing | Exponential delay enforced |
| State preserved | Memory/scrip unchanged |
| Observable | Dashboard shows restarts |

---

## Configuration

```yaml
# config/config.yaml
supervisor:
  enabled: true
  restart_policy:
    max_restarts_per_hour: 10
    initial_backoff_seconds: 5.0
    max_backoff_seconds: 300.0
    backoff_multiplier: 2.0
    restart_on_error: true
    restart_on_timeout: true
    restart_on_resource_exhaustion: false
```

---

## ADRs Applied

- ADR-0014: Continuous Execution Primary (agents should keep running)
- ADR-0011: Standing Pays Costs (smart death = economic, not bugs)

---

## Future Enhancements

- **Health checks**: Periodic liveness probes
- **Circuit breaker**: Disable agent after repeated failures
- **Notification hooks**: Alert on restarts
- **Recovery strategies**: Different strategies per error type
