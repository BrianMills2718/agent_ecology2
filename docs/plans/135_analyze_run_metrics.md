# Plan #135: Run Analysis Metrics Script

**Status:** 📋 Planned
**Priority:** Low
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:** After running a simulation, analyzing results requires manual investigation - grepping logs, counting events, computing rates by hand.

**Target:** A simple `make analyze` command that outputs key metrics from a simulation run.

**Why Low:** Quality-of-life improvement for debugging, not core functionality.

---

## References Reviewed

- `logs/run_*/events.jsonl` - Event log structure
- `llm_logs/` - LLM call logs with success/failure
- Manual analysis done in conversation - identified key metrics

---

## Files Affected

- `scripts/analyze_run.py` (create)
- `Makefile` (modify)

---

## Plan

### Metrics to Output

| Category | Metric | Source |
|----------|--------|--------|
| LLM | Success rate | `llm_logs/*.json` → `metadata.success` |
| LLM | Thought capture rate | `events.jsonl` → `thinking` events with non-empty `thought_process` |
| Actions | Count by agent | `events.jsonl` → `action` events → `intent.principal_id` |
| Actions | Count by type | `events.jsonl` → `action` events → `intent.action_type` |
| Invokes | Success rate | `events.jsonl` → `invoke_success` / `invoke_failure` |
| Invokes | Top failure reasons | `events.jsonl` → `invoke_failure` → `error_message` |
| Artifacts | Created by agent | `events.jsonl` → `write_artifact` successes |
| Economy | Final scrip | `events.jsonl` → last `action` per agent → `scrip_after` |
| Auctions | Winners/mints | `events.jsonl` → `mint_auction_resolved` |

### Output Format

```
=== Run Analysis: run_20260120_134859 ===
Duration: 5m 6s | Events: 1545

LLM PERFORMANCE:
  Success rate:    99.1% (668/674)
  Thought capture: 100%  (668/668)

AGENT ACTIVITY:
  alpha_3:   127 actions (read:71, write:39, invoke:17)
  beta_3:    175 actions (read:84, write:1, invoke:90)
  ...

INVOKE RESULTS:
  Success rate: 94.9% (168/177)
  Top failures:
    - ModuleNotFoundError: pandas (2)
    - ModuleNotFoundError: swarms (2)
    ...

ARTIFACTS CREATED:
  gamma_3: 54 | alpha_3: 34 | delta_3: 31 | ...

ECONOMY:
  alpha_3: 102 (+2) | delta_3: 107 (+7) | ...
  Auctions: 2 resolved, 9 scrip minted
```

### Steps

1. Create `scripts/analyze_run.py` with CLI interface
2. Add `make analyze RUN=<path>` to Makefile
3. Default to `logs/latest` if no RUN specified

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_analyze_run.py` | `test_compute_llm_metrics` | LLM success rate computed correctly |
| `tests/unit/test_analyze_run.py` | `test_compute_agent_actions` | Action counts per agent correct |
| `tests/unit/test_analyze_run.py` | `test_handles_empty_run` | Graceful handling of empty logs |

### Existing Tests (Must Pass)

No existing tests affected - this is a new standalone script.

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Analyze recent run | `make analyze RUN=logs/latest` | Outputs formatted metrics |

---

## Verification

### Tests & Quality
- [ ] Unit tests pass
- [ ] Script runs on actual log files
- [ ] Output is readable and useful

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] Claim released
- [ ] Branch merged

---

## Notes

- Keep it simple - just metrics, no "recommendations"
- Can be extended later if needed
