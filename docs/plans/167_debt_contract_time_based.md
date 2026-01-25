# Plan #167: Debt Contract Time-Based Redesign

**Status:** Planned
**Priority:** Low
**Complexity:** Medium

## Problem

`genesis_debt_contract` still uses tick-based scheduling despite tick removal (Plan #164):
- `due_tick` - when debt is due (tick number)
- Interest calculated based on ticks elapsed

This doesn't work in continuous execution where ticks don't exist.

## Current State

```python
# In genesis/debt_contract.py
class Debt:
    due_tick: int           # When debt is due
    principal: int          # Amount borrowed
    rate: float             # Interest rate (per tick)
```

Interest calculation: `current_owed = principal + (principal * rate * ticks_elapsed)`

## Solution

Replace tick-based with time-based scheduling:

### Phase 1: Schema Update

```python
class Debt:
    due_at: datetime        # When debt is due (timestamp)
    principal: int          # Amount borrowed
    rate_per_day: float     # Interest rate (per day)
    created_at: datetime    # When debt was created
```

### Phase 2: Interest Calculation

```python
def current_owed(self, now: datetime) -> float:
    days_elapsed = (now - self.created_at).total_seconds() / 86400
    interest = self.principal * self.rate_per_day * days_elapsed
    return self.principal + interest - self.amount_paid
```

### Phase 3: Collection Logic

```python
def can_collect(self, now: datetime) -> bool:
    return now >= self.due_at and self.status == "active"
```

### Phase 4: API Updates

| Old | New |
|-----|-----|
| `issue(..., due_tick)` | `issue(..., due_in_seconds)` |
| `check()` returns `due_tick` | `check()` returns `due_at` |

## Testing

- [ ] Create debt with due_in_seconds
- [ ] Interest accrues correctly over time
- [ ] Collection works after due_at
- [ ] Backward compat migration for existing debts

## Files to Modify

| File | Change |
|------|--------|
| `src/world/genesis/debt_contract.py` | Time-based scheduling |
| `tests/unit/test_debt_contract.py` | Update tests |

## Dependencies

- Plan #164: Tick Terminology Purge (complete)

## Notes

This is lower priority since debt contracts are rarely used in current simulations. Can be done opportunistically.
