# INT-001: Integrate RateTracker into Ledger

**Priority:** 1 (BLOCKING - all other Phase 2 work depends on this)
**Complexity:** M
**Risk:** Medium

---

## Summary

Wire the standalone RateTracker module into Ledger so that renewable resources use rolling window rate limiting instead of tick-based refresh.

---

## Current State

- `src/world/rate_tracker.py` exists with full functionality
- `src/world/ledger.py` uses tick-based resource management:
  - `reset_compute(agent_id, amount)` called each tick
  - Flow resources reset at tick boundaries
  - No integration with RateTracker

---

## Target State

- Ledger has a RateTracker instance
- Renewable resources (compute) use RateTracker for capacity checking
- `check_resource_capacity()` and `consume_resource()` methods available
- Feature flag `rate_limiting.enabled` controls behavior
- Legacy tick-based reset still works when flag is False

---

## Files to Modify

| File | Changes |
|------|---------|
| `src/world/ledger.py` | Add RateTracker integration |
| `src/world/world.py` | Pass config to Ledger for RateTracker init |
| `tests/test_ledger.py` | Add tests for new methods |

---

## Implementation Steps

### Step 1: Add RateTracker to Ledger

```python
# In src/world/ledger.py

from src.world.rate_tracker import RateTracker

@dataclass
class Ledger:
    # ... existing fields ...

    # NEW: Rate tracker for renewable resources
    rate_tracker: Optional[RateTracker] = None
    use_rate_tracker: bool = False  # Feature flag

    def __post_init__(self) -> None:
        # Initialize rate tracker if enabled
        if self.use_rate_tracker and self.rate_tracker is None:
            self.rate_tracker = RateTracker()
```

### Step 2: Add Initialization from Config

```python
# In src/world/ledger.py

@classmethod
def from_config(cls, config: dict, agent_ids: list[str]) -> "Ledger":
    """Create Ledger from config with optional RateTracker."""
    rate_limiting_config = config.get("rate_limiting", {})
    use_rate_tracker = rate_limiting_config.get("enabled", False)

    rate_tracker = None
    if use_rate_tracker:
        rate_tracker = RateTracker(
            window_seconds=rate_limiting_config.get("window_seconds", 60.0)
        )
        # Configure limits from config
        resources = rate_limiting_config.get("resources", {})
        for resource_name, resource_config in resources.items():
            max_per_window = resource_config.get("max_per_window", float('inf'))
            rate_tracker.configure_limit(resource_name, max_per_window)

    return cls(
        # ... existing params ...
        rate_tracker=rate_tracker,
        use_rate_tracker=use_rate_tracker,
    )
```

### Step 3: Add Capacity Checking Methods

```python
# In src/world/ledger.py

def check_resource_capacity(
    self,
    agent_id: str,
    resource: str,
    amount: float = 1.0
) -> bool:
    """
    Check if agent has capacity for resource consumption.

    Uses RateTracker if enabled, otherwise always returns True
    (legacy tick-based mode manages resources differently).
    """
    if self.use_rate_tracker and self.rate_tracker:
        return self.rate_tracker.has_capacity(agent_id, resource, amount)
    return True  # Legacy mode: no pre-check

def consume_resource(
    self,
    agent_id: str,
    resource: str,
    amount: float = 1.0
) -> bool:
    """
    Consume resource capacity.

    Uses RateTracker if enabled.
    Returns True if successful, False if insufficient capacity.
    """
    if self.use_rate_tracker and self.rate_tracker:
        return self.rate_tracker.consume(agent_id, resource, amount)
    return True  # Legacy mode: no rate limiting

def get_resource_remaining(
    self,
    agent_id: str,
    resource: str
) -> float:
    """Get remaining capacity for a resource."""
    if self.use_rate_tracker and self.rate_tracker:
        return self.rate_tracker.get_remaining(agent_id, resource)
    return float('inf')  # Legacy mode: unlimited

async def wait_for_resource(
    self,
    agent_id: str,
    resource: str,
    amount: float = 1.0,
    timeout: Optional[float] = None
) -> bool:
    """
    Wait until resource capacity is available.

    Only works with RateTracker enabled.
    Returns True if capacity acquired, False if timeout.
    """
    if self.use_rate_tracker and self.rate_tracker:
        return await self.rate_tracker.wait_for_capacity(
            agent_id, resource, amount, timeout
        )
    return True  # Legacy mode: immediate success
```

### Step 4: Update World to Pass Config

```python
# In src/world/world.py

class World:
    def __init__(self, config: dict, ...):
        # ... existing init ...

        # Create ledger with config for rate limiting
        self.ledger = Ledger.from_config(config, agent_ids)
```

### Step 5: Keep Legacy reset_compute Working

```python
# In src/world/ledger.py

def reset_compute(self, agent_id: str, amount: int) -> None:
    """
    Reset compute for agent (tick-based mode).

    DEPRECATED: Use rate_tracker when rate_limiting.enabled=True.
    This method is kept for backward compatibility.
    """
    if not self.use_rate_tracker:
        # Legacy behavior: reset to quota
        self.compute_balances[agent_id] = amount
    # When using rate_tracker, this is a no-op
    # (rate tracker uses rolling windows, not resets)
```

### Step 6: Add Tests

```python
# In tests/test_ledger.py

class TestRateTrackerIntegration:
    """Tests for Ledger + RateTracker integration."""

    def test_rate_tracker_disabled_by_default(self):
        """Rate tracker not used when disabled."""
        ledger = Ledger(agent_ids=["agent1"])
        assert ledger.use_rate_tracker is False
        assert ledger.check_resource_capacity("agent1", "llm_calls") is True

    def test_rate_tracker_enabled_from_config(self):
        """Rate tracker initialized from config."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 60.0,
                "resources": {
                    "llm_calls": {"max_per_window": 100}
                }
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])
        assert ledger.use_rate_tracker is True
        assert ledger.rate_tracker is not None

    def test_check_capacity_uses_rate_tracker(self):
        """check_resource_capacity delegates to RateTracker."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "resources": {"llm_calls": {"max_per_window": 10}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        assert ledger.check_resource_capacity("agent1", "llm_calls", 5) is True
        ledger.consume_resource("agent1", "llm_calls", 10)
        assert ledger.check_resource_capacity("agent1", "llm_calls", 1) is False

    def test_legacy_mode_still_works(self):
        """Legacy tick-based mode unchanged when disabled."""
        ledger = Ledger(agent_ids=["agent1"], starting_compute=100)
        ledger.reset_compute("agent1", 50)
        assert ledger.get_compute("agent1") == 50

    @pytest.mark.asyncio
    async def test_wait_for_resource(self):
        """wait_for_resource blocks until capacity available."""
        config = {
            "rate_limiting": {
                "enabled": True,
                "window_seconds": 0.1,  # Short window for test
                "resources": {"test": {"max_per_window": 1}}
            }
        }
        ledger = Ledger.from_config(config, ["agent1"])

        # Consume all capacity
        ledger.consume_resource("agent1", "test", 1)

        # Wait should succeed after window expires
        result = await ledger.wait_for_resource("agent1", "test", 1, timeout=0.5)
        assert result is True
```

---

## Interface Definition

```python
class Ledger:
    # Existing methods unchanged...

    # NEW methods for rate limiting
    def check_resource_capacity(self, agent_id: str, resource: str, amount: float = 1.0) -> bool: ...
    def consume_resource(self, agent_id: str, resource: str, amount: float = 1.0) -> bool: ...
    def get_resource_remaining(self, agent_id: str, resource: str) -> float: ...
    async def wait_for_resource(self, agent_id: str, resource: str, amount: float = 1.0, timeout: float | None = None) -> bool: ...

    @classmethod
    def from_config(cls, config: dict, agent_ids: list[str]) -> "Ledger": ...
```

---

## Acceptance Criteria

- [ ] Ledger has optional RateTracker integration
- [ ] `rate_limiting.enabled: true` activates RateTracker
- [ ] `check_resource_capacity()` uses RateTracker when enabled
- [ ] `consume_resource()` deducts from rolling window
- [ ] `wait_for_resource()` blocks until capacity available
- [ ] Legacy `reset_compute()` still works when disabled
- [ ] Feature flag controls which mode is active
- [ ] All existing ledger tests still pass
- [ ] New integration tests pass

---

## Verification

```bash
# Run ledger tests
pytest tests/test_ledger.py -v

# Run all tests
pytest tests/ -v

# Type check
python -m mypy src/world/ledger.py --ignore-missing-imports
```

---

## Dependencies

- **Requires:** GAP-RES-001 (RateTracker) - COMPLETE ✓
- **Blocks:** INT-002, INT-003, CAP-001, CAP-002
