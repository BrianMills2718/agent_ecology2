# Plan 73: Fix Simulation Output Messaging

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Simulation startup output uses confusing/incorrect terminology:
- "Token rates: 1 compute/1K input, 3 compute/1K output" - "compute" is legacy
- "Compute quota/tick: 50" - meaningless in autonomous mode
- "Max ticks: 100" shown even when using `--duration`
- `datetime.utcnow()` deprecation warnings
- Browser doesn't auto-open (WSL limitation - document, don't fix)

**Target:** Output uses correct terminology per `docs/architecture/current/resources.md`:
- Show actual $ costs (the real scarce resource)
- Show rate limits (tokens/window) not abstract "compute"
- Autonomous mode output doesn't reference ticks
- No deprecation warnings

---

## References

- `docs/architecture/current/resources.md` - Canonical terminology
- `docs/GLOSSARY.md` - Term definitions
- Line 22 of resources.md: "Legacy config uses `resources.flow.compute` which maps to `llm_tokens`. The term 'compute' is reserved for future local CPU tracking."

---

## Files Affected

- src/simulation/runner.py (modify - output messages)
- src/world/artifacts.py (modify - datetime deprecation)
- src/world/logger.py (modify - datetime deprecation)
- src/world/invocation_registry.py (modify - datetime deprecation)
- src/world/world.py (modify - datetime deprecation)
- src/agents/memory.py (modify - datetime deprecation)
- run.py (modify - WSL browser note)
- tests/unit/test_runner_output.py (create - output tests)
- docs/architecture/current/agents.md (modify - update verified date)
- docs/architecture/current/artifacts_executor.md (modify - update verified date)
- docs/architecture/current/execution_model.md (modify - update verified date)
- docs/architecture/current/supporting_systems.md (modify - update verified date)

---

## Plan

### Step 1: Fix Deprecation Warnings

Replace `datetime.utcnow()` with `datetime.now(timezone.utc)`:
- `src/world/artifacts.py` lines 334, 411, 494
- `src/world/logger.py` line 246

### Step 2: Fix Runner Output Messages

In `src/simulation/runner.py` `_print_config()`:

**Current (wrong):**
```python
print(f"Max ticks: {self.max_ticks}")  # Shown even in --duration mode
print(f"Token rates: {self.engine.rate_input} compute/1K input, ...")
print(f"Compute quota/tick: {self.world.rights_config.get('default_compute_quota', 50)}")
```

**Fixed:**
```python
# Only show ticks in tick mode
if not autonomous_mode:
    print(f"Max ticks: {self.max_ticks}")
else:
    print(f"Duration: {duration}s")

# Show actual $ cost per token, not abstract compute
print(f"LLM costs: ~${input_cost_per_1k}/1K input, ~${output_cost_per_1k}/1K output")

# Show rate limit, not "compute quota"
print(f"LLM rate limit: {tokens_per_window} tokens/window")
```

### Step 3: Document WSL Browser Limitation

The browser auto-open fails silently in WSL. Add note in output:
```
Dashboard available at: http://localhost:9000
(Note: In WSL, open this URL manually in your browser)
```

---

## Required Tests

### Unit Tests

Tests are in `tests/unit/test_runner_output.py`:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_runner_output.py` | `test_autonomous_output_no_ticks` | --duration mode doesn't show "Max ticks" |
| `tests/unit/test_runner_output.py` | `test_tick_mode_shows_ticks` | --ticks mode shows "Max ticks" |
| `tests/unit/test_runner_output.py` | `test_output_uses_llm_terminology` | Output uses "LLM" not "compute" |
| `tests/unit/test_runner_output.py` | `test_shows_rate_limit_when_enabled` | Shows rate limit when enabled |
| `tests/unit/test_runner_output.py` | `test_hides_rate_limit_when_unlimited` | Hides rate limit when unlimited |
| `tests/unit/test_runner_output.py` | `test_no_utcnow_in_artifacts` | No datetime.utcnow() in artifacts.py |
| `tests/unit/test_runner_output.py` | `test_no_utcnow_in_logger` | No datetime.utcnow() in logger.py |
| `tests/unit/test_runner_output.py` | `test_no_utcnow_in_invocation_registry` | No datetime.utcnow() in invocation_registry.py |
| `tests/unit/test_runner_output.py` | `test_no_utcnow_in_memory` | No datetime.utcnow() in memory.py |

---

## Verification

### Tests & Quality
- [ ] All unit tests pass
- [ ] No deprecation warnings in output
- [ ] `--duration 10` output doesn't mention ticks
- [ ] Output uses $ costs not "compute" units

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index updated
- [ ] Claim released
- [ ] PR created/merged

---

## Notes

### Design Decisions

1. **Show actual $ costs** - LLM budget is the real depletable resource
2. **Rate limits in tokens/window** - Matches RateTracker implementation
3. **Mode-specific output** - Don't mix tick and duration concepts

### Out of Scope

- Renaming all internal "compute" variables (too invasive)
- Fixing WSL browser issue (OS limitation)

