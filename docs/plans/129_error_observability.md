# Plan #129: Error Observability

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None
**Blocks:** Debugging efficiency, operational awareness

**Scope:** Phases 1-3 only (startup validation, error aggregation, console summary). Dashboard integration deferred.

## Problem

When the simulation fails, diagnosing the root cause requires manually digging through JSON files in `llm_logs/`. Common issues like:
- Invalid/unavailable LLM models
- API quota exhaustion
- Schema validation errors
- Rate limiting

...are not surfaced clearly. The user discovered `gemini-3-flash-preview` had quota 0 only after reading raw JSON error logs.

## Goals

1. **Fail fast on invalid config** - Validate LLM model availability at startup
2. **Surface errors prominently** - Show error summary in console and dashboard
3. **Track error metrics** - Add error rate to ecosystem KPIs
4. **Actionable error messages** - Include fix suggestions in error output

## Implementation

### Phase 1: Startup Validation

**File:** `run.py` or new `src/validation.py`

```python
def validate_llm_config():
    """Validate LLM model is available before starting simulation."""
    model = config.get("llm.default_model")

    # Also check agent-specific models
    for agent_dir in Path("src/agents").iterdir():
        agent_yaml = agent_dir / "agent.yaml"
        if agent_yaml.exists():
            agent_config = yaml.safe_load(agent_yaml.read_text())
            agent_model = agent_config.get("llm_model", model)
            # Validate each unique model
```

Options for validation:
1. **Dry-run API call** - Make a minimal API call to verify credentials/model
2. **Model list check** - Check against litellm's known model list
3. **Config consistency** - Warn if agent models differ from default

### Phase 2: Error Aggregation in Runner

**File:** `src/simulation/runner.py`

Track errors during simulation:

```python
@dataclass
class ErrorStats:
    total_errors: int = 0
    by_type: dict[str, int] = field(default_factory=dict)
    by_agent: dict[str, int] = field(default_factory=dict)
    recent_errors: list[dict] = field(default_factory=list)  # Last 10

class SimulationRunner:
    def __init__(self):
        self.error_stats = ErrorStats()

    def _record_error(self, error_type: str, agent_id: str, message: str):
        self.error_stats.total_errors += 1
        self.error_stats.by_type[error_type] = self.error_stats.by_type.get(error_type, 0) + 1
        # ...
```

### Phase 3: Console Error Summary

Print error summary on shutdown:

```
=== Simulation Error Summary ===
Total errors: 15
By type:
  RateLimitError: 10 (66%)
  BadRequestError: 5 (33%)
By agent:
  alpha_3: 5
  beta_3: 4
  ...

Most recent error:
  Type: RateLimitError
  Message: Quota exceeded for gemini-3-flash-preview
  Suggestion: Check your API quota or switch to gemini-2.5-flash
```

### Phase 4: Dashboard Error Panel

**File:** `src/dashboard/server.py`, `src/dashboard/static/`

Add `/api/errors` endpoint:

```python
@app.get("/api/errors")
async def get_errors():
    return {
        "total": runner.error_stats.total_errors,
        "by_type": runner.error_stats.by_type,
        "recent": runner.error_stats.recent_errors[-10:],
        "error_rate": calculate_error_rate(),
    }
```

Dashboard UI:
- Error count badge in header
- Collapsible error panel showing recent errors
- Error type breakdown chart

### Phase 5: Error KPIs

**File:** `src/dashboard/kpis.py`

Add to `EcosystemKPIs`:

```python
class EcosystemKPIs:
    # ... existing fields ...
    llm_error_rate: float = 0.0  # errors / total_calls
    llm_errors_by_type: dict[str, int] = field(default_factory=dict)
```

### Phase 6: Actionable Error Messages

Create error-to-suggestion mapping:

```python
ERROR_SUGGESTIONS = {
    "RateLimitError": "API rate limit hit. Options: 1) Wait and retry, 2) Reduce concurrent agents, 3) Increase rate_limit_delay in config",
    "RESOURCE_EXHAUSTED": "API quota exhausted. Check your billing at https://ai.google.dev/",
    "BadRequestError.*properties.*non-empty": "Schema incompatible with model. The interface field may need adjustment.",
    "AuthenticationError": "Invalid API key. Check GEMINI_API_KEY in .env",
}

def get_error_suggestion(error_message: str) -> str | None:
    for pattern, suggestion in ERROR_SUGGESTIONS.items():
        if re.search(pattern, error_message):
            return suggestion
    return None
```

## Files Affected

- run.py (modify - startup validation, shutdown summary)
- src/simulation/runner.py (modify - ErrorStats tracking)
- src/simulation/types.py (modify - add ErrorStats dataclass)
- docs/plans/129_error_observability.md (create - this plan, renumbered from 118)
- docs/plans/118_computed_plan_status.md (modify - mark as Deferred)

*Dashboard integration (Phases 4-6) deferred to future plan.*

## Testing

```bash
# Unit tests
pytest tests/unit/test_error_observability.py -v

# Integration tests
pytest tests/integration/test_error_reporting.py -v

# Manual verification
# 1. Configure invalid model, verify startup warning
# 2. Run sim with rate limiting, verify error summary
# 3. Check dashboard error panel
```

## Acceptance Criteria (Phases 1-3)

- [x] Startup warns if configured LLM model is invalid/unavailable
- [x] Errors tracked during simulation (type, agent, message)
- [x] Shutdown prints error summary with counts by type
- [x] Common errors include actionable suggestions

## Notes

- Phase 1 (startup validation) provides most immediate value
- Consider making validation optional via `--skip-validation` flag for offline testing
- Error suggestions should be configurable in `config.yaml`
