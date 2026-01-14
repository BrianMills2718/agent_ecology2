# CC-1 Task Investigation

## Task 1: Fix Float Precision in Ledger

### Files to Touch
- `src/world/ledger.py` - Main changes
- `tests/test_ledger.py` - Add precision tests

### Current State
```python
# Line 45
resources: dict[str, dict[str, float]]

# Line 86 - subtraction
self.resources[principal_id][resource] = self.get_resource(principal_id, resource) - amount

# Line 94 - addition
self.resources[principal_id][resource] = current + amount
```

### The Problem
Float arithmetic has precision issues:
```python
>>> 0.1 + 0.2
0.30000000000000004
>>> 0.1 + 0.1 + 0.1 - 0.3
5.551115123125783e-17
```

After many operations, balances could drift from expected values.

### Solution Options

**Option A: Use Decimal (Recommended)**
- Exact decimal arithmetic
- `from decimal import Decimal`
- Change `dict[str, float]` to `dict[str, Decimal]`
- Serialize to string for JSON

**Option B: Use int with scaling**
- Store as millitokens (int)
- Divide by 1000 for display
- More complex API changes

### Concerns
1. **Backward compatibility**: Existing checkpoints may have float values
2. **JSON serialization**: Decimal not directly serializable (need str conversion)
3. **API surface**: Many methods take/return float - need to update

### Recommendation
Use Decimal internally but accept float in API, convert at boundary:
```python
def credit_resource(self, principal_id: str, resource: str, amount: float) -> None:
    current = self.resources[principal_id].get(resource, Decimal("0"))
    self.resources[principal_id][resource] = current + Decimal(str(amount))
```

---

## Task 2: Fix Race Condition in Singleton

### Files to Touch
- `src/agents/memory.py` - Add threading.Lock

### Current State (Lines 102-110)
```python
class AgentMemory:
    _instance: "AgentMemory | None" = None
    _initialized: bool

    def __new__(cls) -> "AgentMemory":
        if cls._instance is None:                    # Thread A reads None
            cls._instance = super().__new__(cls)     # Thread B also reads None
            cls._instance._initialized = False       # Both create instances!
        return cls._instance
```

### The Problem
Classic TOCTOU (time-of-check-time-of-use) race condition. Two threads could:
1. Both check `_instance is None` → True
2. Both create new instances
3. Memory leak, inconsistent state

### Solution
```python
import threading

class AgentMemory:
    _instance: "AgentMemory | None" = None
    _lock: threading.Lock = threading.Lock()  # Class-level lock

    def __new__(cls) -> "AgentMemory":
        if cls._instance is None:
            with cls._lock:
                # Double-check after acquiring lock
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
```

### Concerns
1. **Lock overhead**: Minimal - only acquired on first access
2. **Testing**: Hard to test race conditions directly
3. **Deadlock risk**: None - single lock, no nesting

### Recommendation
Use double-checked locking pattern (shown above). Simple and safe.

---

## Task 3: Extract Timeout Helper in Executor

### Files to Touch
- `src/world/executor.py` - Extract helper, refactor 4 call sites

### Current State
Timeout pattern duplicated 4 times:
- Lines 247-266 (execute - code definition)
- Lines 288-306 (execute - run() call)
- Lines 451-467 (execute_with_wallet - code definition)
- Lines 489-506 (execute_with_wallet - run() call)

### The Pattern (repeated verbatim)
```python
old_handler: Any = None
try:
    old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
    signal.alarm(self.timeout)
except (ValueError, AttributeError):
    pass

try:
    # actual work here
finally:
    try:
        signal.alarm(0)
        if old_handler:
            signal.signal(signal.SIGALRM, old_handler)
    except (ValueError, AttributeError):
        pass
```

### Solution: Context Manager
```python
from contextlib import contextmanager
from typing import Generator

@contextmanager
def _timeout_context(timeout: int) -> Generator[None, None, None]:
    """Context manager for Unix signal-based timeout.

    On Windows/platforms without signal.alarm, silently does nothing.
    """
    old_handler: Any = None
    try:
        old_handler = signal.signal(signal.SIGALRM, _timeout_handler)
        signal.alarm(timeout)
    except (ValueError, AttributeError):
        # signal.alarm not available (Windows)
        pass

    try:
        yield
    finally:
        try:
            signal.alarm(0)
            if old_handler:
                signal.signal(signal.SIGALRM, old_handler)
        except (ValueError, AttributeError):
            pass
```

### Usage After Refactor
```python
with _timeout_context(self.timeout):
    exec(compiled, controlled_globals)
```

### Concerns
1. **Exception propagation**: TimeoutError must propagate out - verified, `yield` does this
2. **Nested timeouts**: Each context restores old handler - should work correctly
3. **Testing**: Can test context manager in isolation

### Recommendation
Create `_timeout_context()` context manager, replace all 4 occurrences.

---

## Implementation Order

1. **Task 3 first** (simplest, no API changes, self-contained)
2. **Task 2 second** (simple, low risk)
3. **Task 1 last** (most complex, API changes, backward compat)

## Test Plan

After each task:
```bash
pytest tests/ -q
python -m mypy src/ --ignore-missing-imports
```

## Files Summary

| Task | Files to Modify | Files to Add/Update Tests |
|------|-----------------|---------------------------|
| 1 | src/world/ledger.py | tests/test_ledger.py |
| 2 | src/agents/memory.py | (hard to test directly) |
| 3 | src/world/executor.py | tests/test_executor.py (optional) |
