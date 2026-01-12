# Gap 1: Rate Allocation (Token Bucket)

**Status:** 📋 Planned
**Priority:** High
**Blocked By:** None
**Blocks:** #2 Continuous Execution, #31 Resource Measurement

---

## Gap

### Current
- Flow resources (compute/llm_tokens) reset each tick
- `advance_tick()` sets balance to quota, discarding unused
- Use-or-lose within tick boundaries

### Target
- Rolling window accumulation (token bucket algorithm)
- Continuous accumulation up to capacity
- No discrete reset moments
- Debt allowed (negative balance)

---

## Changes

### Files to Modify

| File | Change |
|------|--------|
| `src/world/ledger.py` | Add TokenBucket class, replace resource tracking |
| `src/world/world.py` | Remove flow reset from `advance_tick()` |
| `src/simulation/runner.py` | Remove tick-based resource logic |
| `config/config.yaml` | Change `per_tick` to `rate` and `capacity` |
| `src/config_schema.py` | Update FlowResource schema |

### New Files

| File | Purpose |
|------|---------|
| `src/world/token_bucket.py` | TokenBucket class implementation |
| `tests/test_token_bucket.py` | Unit tests for token bucket |

---

## Token Bucket Implementation

```python
# src/world/token_bucket.py

import time
from dataclasses import dataclass, field

@dataclass
class TokenBucket:
    """Rolling window resource accumulator."""

    rate: float           # Tokens per second
    capacity: float       # Max tokens (cap)
    balance: float = 0.0  # Current balance (can be negative)
    last_update: float = field(default_factory=time.time)

    def _accumulate(self) -> None:
        """Add tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        self.balance = min(self.capacity, self.balance + elapsed * self.rate)
        self.last_update = now

    def available(self) -> float:
        """Get current available balance."""
        self._accumulate()
        return max(0, self.balance)

    def balance_including_debt(self) -> float:
        """Get balance including negative (debt)."""
        self._accumulate()
        return self.balance

    def spend(self, amount: float) -> bool:
        """Spend tokens. Returns True if was affordable, False if went into debt."""
        self._accumulate()
        was_affordable = self.balance >= amount
        self.balance -= amount
        return was_affordable

    def can_afford(self, amount: float) -> bool:
        """Check if can afford without spending."""
        self._accumulate()
        return self.balance >= amount

    def is_in_debt(self) -> bool:
        """Check if balance is negative."""
        self._accumulate()
        return self.balance < 0
```

---

## Config Changes

### Current
```yaml
resources:
  flow:
    compute:
      per_tick: 1000
      unit: token_units
```

### Target
```yaml
resources:
  flow:
    compute:
      rate: 10.0          # tokens per second
      capacity: 100.0     # max tokens
      unit: token_units
```

---

## Steps

### Step 1: Create TokenBucket class
- Implement `src/world/token_bucket.py`
- Add comprehensive tests

### Step 2: Update config schema
- Change `per_tick` to `rate` and `capacity`
- Update `src/config_schema.py`
- Update `config/config.yaml`

### Step 3: Integrate into Ledger
- Replace resource dict with TokenBucket per principal
- Update `spend_resource()`, `can_spend_resource()`, etc.
- Add `is_in_debt()` method

### Step 4: Remove tick reset
- Remove flow reset from `world.py:advance_tick()`
- Token buckets self-accumulate on access

### Step 5: Update tests
- Update existing tests that depend on tick reset
- Add integration tests

---

## Verification

### Unit Tests
- Token accumulation over time
- Spending and debt
- Capacity capping
- Multiple principals

### Integration Tests
- Agent thinking with token bucket
- Debt blocking actions
- Recovery from debt

### Manual Test
```bash
# Run with low capacity, watch agents go into debt
python run.py --ticks 10 --agents 3
# Observe agents waiting when in debt
```

---

## Rollback

If issues arise:
1. Revert config to `per_tick`
2. Revert ledger to dict-based resources
3. Restore `advance_tick()` flow reset

---

## Dependencies

- None (can be implemented independently)

## Blocks

- Continuous execution (needs token bucket first)
- Debt model (uses token bucket's debt feature)
