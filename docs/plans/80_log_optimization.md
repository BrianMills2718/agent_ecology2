# Plan 80: Log Optimization

**Status:** ✅ Complete

**Verified:** 2026-01-19T05:19:24Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-19T05:19:24Z
tests:
  unit: 1713 passed, 9 skipped, 3 warnings in 37.50s
  e2e_smoke: PASSED (3.33s)
  e2e_real: PASSED (25.16s)
  doc_coupling: passed
commit: 20a1365
```
**Priority:** Medium
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** Log files grow unbounded, reaching 5+ GB for longer runs. The primary cause is large `ActionResult.data` payloads being logged verbatim, especially when agents read the event log (creating recursive event-within-event structures).

**Target:** Bounded log sizes through consistent truncation of logged payloads while maintaining full observability for debugging.

**Why Medium:** Impacts developer experience and disk usage but doesn't affect core simulation mechanics.

---

## References Reviewed

- `src/world/logger.py:1-280` - EventLogger, SummaryLogger implementation
- `src/world/actions.py:190-205` - ActionResult.to_dict() includes full data field
- `src/world/world.py:743-751` - _log_action() logs intent + full result
- `src/simulation/runner.py:627-751` - Thinking/intent logging
- `src/world/genesis/event_log.py:58-92` - GenesisEventLog returns events with data
- `config/config.yaml` - Existing truncation limits (content: 100, code: 100, errors: 100)
- `docs/plans/60_tractable_logs.md` - Related plan (Complete) - per-tick summaries

---

## Files Affected

- src/world/logger.py (modify)
- src/world/actions.py (modify)
- src/world/world.py (modify)
- src/config_schema.py (modify)
- config/schema.yaml (modify)
- config/config.yaml (modify)
- tests/unit/test_log_truncation.py (create)
- docs/architecture/current/execution_model.md (modify)
- docs/architecture/current/artifacts_executor.md (modify)
- docs/architecture/current/configuration.md (modify)

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/actions.py` | Add `to_dict_truncated(max_data_size: int)` method to ActionResult |
| `src/world/logger.py` | Use truncated version when logging actions |
| `config/schema.yaml` | Add `logging.truncation.result_data` config option |
| `config/config.yaml` | Set default result_data truncation (e.g., 1000 chars) |

### Steps

1. Add `to_dict_truncated()` method to ActionResult that:
   - Truncates `data` field if it exceeds configured size
   - Replaces with `{"_truncated": true, "original_size": N, "preview": "..."}`
   - Preserves all other fields (success, message, error_code, etc.)

2. Update EventLogger to use truncated version for action events

3. Add config option for max result data size

4. Create tests verifying truncation behavior

---

## Required Tests

- `tests/unit/test_log_truncation.py::TestActionResultTruncation::test_action_result_truncation_small_data`
- `tests/unit/test_log_truncation.py::TestActionResultTruncation::test_action_result_truncation_large_data`
- `tests/unit/test_log_truncation.py::TestActionResultTruncation::test_truncation_preserves_other_fields`
- `tests/unit/test_log_truncation.py::TestActionResultTruncation::test_nested_data_truncation`
- `tests/unit/test_log_truncation.py::TestActionResultTruncation::test_truncation_config_respected`

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Log size bounded | 1. Run simulation with agents reading event log 2. Check log file size | Log file stays under reasonable size |

```bash
# Run E2E verification
pytest tests/e2e/test_smoke.py -v
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 80`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] E2E verification passes: `pytest tests/e2e/test_smoke.py -v`

### Documentation
- [ ] Config changes documented in schema.yaml comments
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

- Keep full data available via genesis event log for agents who need it
- Truncation only affects what gets written to log files, not runtime behavior
- Consider future extensions: event sampling for long runs, compression at rest
