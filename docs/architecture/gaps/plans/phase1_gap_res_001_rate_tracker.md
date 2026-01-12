# GAP-RES-001: RateTracker Class Implementation Plan

**Gap ID:** GAP-RES-001
**Complexity:** L (200-500 lines)
**Risk:** Medium
**Phase:** 1 - Foundations

---

## Summary

Implement rolling window rate limiting to replace tick-based resource refresh. This is foundational because all resource-gated operations will depend on this mechanism.

---

## Current State

- Resources reset at tick boundaries (`ledger.py`)
- No capacity checking before action attempts
- Agents cannot wait for capacity - actions simply fail
- Rate limits are tick-scoped, not time-scoped

---

## Target State

- Rolling window rate tracking (e.g., 100 LLM calls per 60 seconds)
- `has_capacity(agent_id, resource, amount)` check
- `consume(agent_id, resource, amount)` deduction
- `wait_for_capacity(agent_id, resource, amount)` async blocking
- No tick dependency for rate limiting

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/world/rate_tracker.py` | **NEW FILE** - RateTracker class |
| `src/world/ledger.py` | Replace tick-based refresh with RateTracker |
| `src/world/world.py` | Initialize RateTracker instance |
| `config/schema.yaml` | Add rate window configuration |
| `tests/test_rate_tracker.py` | **NEW FILE** - Unit tests |

---

## Implementation Steps

### Step 1: Create RateTracker Class

Create `src/world/rate_tracker.py`:

```python
from dataclasses import dataclass, field
from typing import Dict, Optional
from collections import deque
import asyncio
import time

@dataclass
class UsageRecord:
    """Single usage event with timestamp."""
    timestamp: float
    amount: float

@dataclass
class RateTracker:
    """Rolling window rate limiter for resources."""

    window_seconds: float = 60.0
    # resource_type -> agent_id -> deque of UsageRecords
    _usage: Dict[str, Dict[str, deque]] = field(default_factory=dict)
    # resource_type -> max_per_window
    _limits: Dict[str, float] = field(default_factory=dict)

    def configure_limit(self, resource: str, max_per_window: float) -> None:
        """Set rate limit for a resource type."""
        self._limits[resource] = max_per_window
        if resource not in self._usage:
            self._usage[resource] = {}

    def _clean_old_records(self, resource: str, agent_id: str) -> None:
        """Remove records outside the rolling window."""
        if resource not in self._usage:
            return
        if agent_id not in self._usage[resource]:
            return

        cutoff = time.time() - self.window_seconds
        records = self._usage[resource][agent_id]
        while records and records[0].timestamp < cutoff:
            records.popleft()

    def get_usage(self, agent_id: str, resource: str) -> float:
        """Get current usage within the rolling window."""
        self._clean_old_records(resource, agent_id)

        if resource not in self._usage:
            return 0.0
        if agent_id not in self._usage[resource]:
            return 0.0

        return sum(r.amount for r in self._usage[resource][agent_id])

    def get_remaining(self, agent_id: str, resource: str) -> float:
        """Get remaining capacity in current window."""
        limit = self._limits.get(resource, float('inf'))
        usage = self.get_usage(agent_id, resource)
        return max(0.0, limit - usage)

    def has_capacity(self, agent_id: str, resource: str, amount: float = 1.0) -> bool:
        """Check if agent has capacity for the requested amount."""
        return self.get_remaining(agent_id, resource) >= amount

    def consume(self, agent_id: str, resource: str, amount: float = 1.0) -> bool:
        """
        Consume resource capacity.
        Returns True if successful, False if insufficient capacity.
        """
        if not self.has_capacity(agent_id, resource, amount):
            return False

        if resource not in self._usage:
            self._usage[resource] = {}
        if agent_id not in self._usage[resource]:
            self._usage[resource][agent_id] = deque()

        self._usage[resource][agent_id].append(
            UsageRecord(timestamp=time.time(), amount=amount)
        )
        return True

    async def wait_for_capacity(
        self,
        agent_id: str,
        resource: str,
        amount: float = 1.0,
        timeout: Optional[float] = None
    ) -> bool:
        """
        Wait until capacity is available.
        Returns True if capacity acquired, False if timeout.
        """
        start = time.time()
        while not self.has_capacity(agent_id, resource, amount):
            if timeout and (time.time() - start) >= timeout:
                return False
            # Calculate sleep time based on oldest record expiry
            await asyncio.sleep(0.1)  # Poll interval

        return self.consume(agent_id, resource, amount)

    def time_until_capacity(self, agent_id: str, resource: str, amount: float = 1.0) -> float:
        """Estimate seconds until capacity is available."""
        if self.has_capacity(agent_id, resource, amount):
            return 0.0

        self._clean_old_records(resource, agent_id)

        if resource not in self._usage or agent_id not in self._usage[resource]:
            return 0.0

        records = self._usage[resource][agent_id]
        if not records:
            return 0.0

        # Find when enough old records will expire
        limit = self._limits.get(resource, float('inf'))
        needed = amount - (limit - self.get_usage(agent_id, resource))

        accumulated = 0.0
        for record in records:
            accumulated += record.amount
            if accumulated >= needed:
                return max(0.0, record.timestamp + self.window_seconds - time.time())

        return self.window_seconds  # Worst case: full window
```

### Step 2: Add Configuration

Update `config/schema.yaml`:

```yaml
rate_limiting:
  window_seconds: 60.0
  resources:
    llm_calls:
      max_per_window: 100
    disk_writes:
      max_per_window: 1000
    bandwidth_bytes:
      max_per_window: 10485760  # 10MB
```

### Step 3: Integrate with Ledger

Update `src/world/ledger.py`:
- Import RateTracker
- Add `rate_tracker` field to Ledger
- Replace tick-based checks with `rate_tracker.has_capacity()`
- Replace tick-based consumption with `rate_tracker.consume()`

### Step 4: Initialize in World

Update `src/world/world.py`:
- Create RateTracker instance from config
- Pass to Ledger during initialization

### Step 5: Create Tests

Create `tests/test_rate_tracker.py`:
- Test `has_capacity()` returns True when under limit
- Test `has_capacity()` returns False when at limit
- Test `consume()` reduces remaining capacity
- Test rolling window - old records expire
- Test `wait_for_capacity()` blocks and succeeds
- Test `wait_for_capacity()` timeout
- Test `time_until_capacity()` estimates correctly

---

## Interface Definition

```python
class RateTracker(Protocol):
    def configure_limit(self, resource: str, max_per_window: float) -> None: ...
    def has_capacity(self, agent_id: str, resource: str, amount: float = 1.0) -> bool: ...
    def consume(self, agent_id: str, resource: str, amount: float = 1.0) -> bool: ...
    async def wait_for_capacity(self, agent_id: str, resource: str, amount: float = 1.0, timeout: float | None = None) -> bool: ...
    def get_remaining(self, agent_id: str, resource: str) -> float: ...
    def time_until_capacity(self, agent_id: str, resource: str, amount: float = 1.0) -> float: ...
```

---

## Migration Strategy

1. Implement RateTracker alongside existing tick-based system
2. Add feature flag `use_rate_tracker` (default: False)
3. When enabled, use RateTracker instead of tick counters
4. Run parallel in tests to verify equivalent behavior
5. Enable by default after validation
6. Remove tick-based code in Phase 2

---

## Test Cases

| Test | Description | Expected |
|------|-------------|----------|
| `test_initial_capacity` | Fresh tracker has full capacity | `has_capacity() == True` |
| `test_consume_reduces` | Consuming reduces remaining | `get_remaining()` decreases |
| `test_over_limit_fails` | Consume over limit returns False | `consume() == False` |
| `test_window_expiry` | Old records drop off after window | Capacity restored |
| `test_wait_blocks` | `wait_for_capacity` waits for expiry | Returns True after wait |
| `test_wait_timeout` | Timeout returns False | `wait_for_capacity() == False` |
| `test_multiple_agents` | Agents have independent limits | Each agent has own capacity |
| `test_multiple_resources` | Resources tracked separately | Independent limits |

---

## Acceptance Criteria

- [ ] RateTracker class implemented with all methods
- [ ] Rolling window correctly expires old records
- [ ] `has_capacity()` accurately reflects available capacity
- [ ] `consume()` atomically checks and deducts
- [ ] `wait_for_capacity()` blocks until available or timeout
- [ ] Configuration schema defines rate limits
- [ ] All tests pass
- [ ] No tick dependency for rate limiting

---

## Rollback Plan

If issues arise:
1. Set `use_rate_tracker: false` in config
2. System falls back to tick-based refresh
3. Debug RateTracker in isolation
4. Fix and re-enable

---

## Dependencies

- **Blocks:** GAP-EXEC-002 (agent sleep system needs capacity checking)
- **Blocks:** GAP-RES-019 (action blocking vs skip)
- **Required by:** Phase 2 execution stream
