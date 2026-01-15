# Gap 56: Per-Run Logging

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** `EventLogger` overwrites `run.jsonl` on every new simulation run (clears file on init). Previous run data is lost. The `log_dir` config exists but isn't used for event logs.

**Target:** Per-run log organization:
- Each run creates a timestamped directory: `logs/run_YYYYMMDD_HHMMSS/`
- Event log saved to `logs/run_YYYYMMDD_HHMMSS/events.jsonl`
- Previous runs preserved for comparison and analysis
- Symlink `logs/latest/` points to most recent run

**Why Medium:** Improves developer experience and enables run comparison. Not critical for V1 but highly useful.

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/logger.py` | UPDATE - Use timestamped directories, add run_id parameter |
| `src/simulation/runner.py` | UPDATE - Pass run_id to EventLogger |
| `config/schema.yaml` | UPDATE - Add `logging.logs_dir` description |
| `config/config.yaml` | UPDATE - Set default `logs_dir: "logs"` |
| `docs/architecture/current/resources.md` | UPDATE - Document per-run logging |

### Steps

1. Modify `EventLogger.__init__()` to accept optional `run_id` parameter
2. When `run_id` provided, create directory `{logs_dir}/{run_id}/`
3. Write events to `{logs_dir}/{run_id}/events.jsonl`
4. Create/update symlink `{logs_dir}/latest` -> `{run_id}/`
5. Pass `run_id` from SimulationRunner to EventLogger
6. Update documentation

---

## Required Tests

### New Tests (TDD)

Create these tests FIRST, before implementing:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_logger.py` | `test_per_run_directory_created` | Directory created with run_id |
| `tests/unit/test_logger.py` | `test_events_written_to_run_directory` | Events go to correct path |
| `tests/unit/test_logger.py` | `test_latest_symlink_created` | Symlink points to latest run |
| `tests/unit/test_logger.py` | `test_multiple_runs_preserved` | Previous runs not overwritten |
| `tests/unit/test_logger.py` | `test_backward_compat_no_run_id` | Works without run_id (legacy mode) |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/e2e/test_smoke.py` | Full simulation works |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Multiple runs preserved | 1. Run simulation twice 2. Check logs/ directory | Two timestamped directories exist, both have events.jsonl |

```bash
# Run E2E verification
pytest tests/e2e/test_smoke.py -v
# Then manually verify: ls -la logs/
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 56`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] E2E verification passes: `pytest tests/e2e/test_smoke.py -v`

### Documentation
- [ ] `docs/architecture/current/resources.md` updated with per-run logging
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status -> `✅ Complete`
- [ ] `plans/CLAUDE.md` index -> `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

- Existing `docs/meta/12_structured-logging.md` documents an ideal pattern but was never implemented
- The `run_id` is already generated in SimulationRunner (`run_YYYYMMDD_HHMMSS`)
- Backward compatibility: if no run_id provided, use legacy single-file mode
