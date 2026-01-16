# Gap 60: Tractable Logs

**Status:** 🚧 In Progress
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** Only full JSONL event logs exist (`events.jsonl`). The `view_log.py` script provides basic summary but requires manual invocation. No condensed/summary view for quick understanding of run behavior.

**Target:** Generate tractable summary logs alongside full logs:
- `summary.jsonl` - One line per tick with key metrics
- Human-readable report generation
- Dashboard summary endpoint

**Why Medium:** Improves developer experience and debugging. Full logs are overwhelming for understanding overall behavior.

---

## Plan

### Changes Required
| File | Change |
|------|--------|
| `src/world/logger.py` | Add `SummaryLogger` class that writes per-tick summaries |
| `src/simulation/runner.py` | Hook summary logger into tick lifecycle |
| `scripts/view_log.py` | Add `--report` option for markdown report |
| `src/dashboard/server.py` | Add `/api/summary` endpoint |
| `src/dashboard/models.py` | Add `RunSummary` model |

### Summary Log Format

Each line in `summary.jsonl`:
```json
{
  "tick": 5,
  "timestamp": "2026-01-16T12:00:00Z",
  "agents_active": 3,
  "actions_executed": 3,
  "actions_by_type": {"invoke": 2, "write": 1},
  "total_llm_tokens": 150,
  "total_scrip_transferred": 25,
  "artifacts_created": 1,
  "errors": 0,
  "highlights": ["alpha created tool_x", "beta transferred 25 scrip to gamma"]
}
```

### Steps
1. Create `SummaryLogger` class in `src/world/logger.py`
2. Add tick summary collection to `SimulationRunner`
3. Write summary at end of each tick
4. Add `--report` option to `view_log.py` for markdown report
5. Add `/api/summary` dashboard endpoint
6. Update docs

---

## Required Tests

### New Tests (TDD)

Create these tests FIRST, before implementing:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_summary_logger.py` | `test_writes_one_line_per_tick` | SummaryLogger writes one line per tick |
| `tests/unit/test_summary_logger.py` | `test_summary_format_has_required_fields` | Summary JSON has required fields |
| `tests/unit/test_summary_logger.py` | `test_event_logger_creates_summary_logger` | EventLogger creates companion SummaryLogger |
| `tests/unit/test_summary_logger.py` | `test_tick_summary_collector_tracks_actions` | TickSummaryCollector tracks actions |
| `tests/unit/test_summary_logger.py` | `test_tick_summary_collector_tracks_llm_tokens` | TickSummaryCollector tracks tokens |
| `tests/unit/test_summary_logger.py` | `test_tick_summary_collector_tracks_scrip` | TickSummaryCollector tracks scrip |
| `tests/unit/test_summary_logger.py` | `test_tick_summary_collector_captures_highlights` | TickSummaryCollector captures highlights |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/integration/test_runner.py` | Runner behavior unchanged |
| `tests/unit/test_logger.py` | Existing logger tests |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Summary log generated | 1. Run `python run.py --ticks 5` 2. Check `logs/latest/` | `summary.jsonl` exists with 5 lines |
| Report generation | 1. Run simulation 2. Run `python scripts/view_log.py --report` | Markdown report output |

```bash
# Run E2E verification
python run.py --ticks 5
ls logs/latest/summary.jsonl
python scripts/view_log.py logs/latest/events.jsonl --report
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 60`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/supporting_systems.md` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

- Summary log is append-only like events.jsonl
- Highlights are auto-generated from significant events (artifact creation, transfers > threshold, errors)
- Consider adding scrip velocity, Gini coefficient to per-tick summary for trend analysis
