# Gap 31: Resource Measurement

**Status:** ✅ Complete
**Priority:** High
**Blocked By:** #1
**Blocks:** None

---

## Gap

**Current:** Only LLM tokens and disk tracked

**Target:** All resources tracked in natural units

---

## Implementation

Added to `src/world/simulation_engine.py`:

| Class/Function | Purpose |
|----------------|---------|
| `ResourceUsage` | Dataclass holding cpu_seconds, peak_memory_bytes, disk_bytes_written |
| `ResourceMeasurer` | Context manager using time.process_time() and tracemalloc |
| `measure_resources()` | Convenience generator function |

### Usage

```python
from src.world.simulation_engine import measure_resources

with measure_resources() as usage:
    # Do work
    pass
print(usage.cpu_seconds, usage.peak_memory_bytes)
```

---

## Verification

- [x] Tests pass (`tests/test_simulation_engine.py` - 45 tests)
- [x] Docs updated (`docs/architecture/current/resources.md`)
- [x] Implementation matches target

---

## Notes

Completed 2026-01-12. PR #10 merged.

See GAPS.md archive for detailed context.
