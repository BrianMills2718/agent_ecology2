# Plan #251: Resource Terminology Cleanup

**Status:** ✅ Complete

**Verified:** 2026-02-02T01:54:24Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-02-02T01:54:24Z
tests:
  unit: skipped (--status-only, CI-validated)
  e2e_smoke: skipped (--status-only, CI-validated)
  e2e_real: skipped (--status-only, CI-validated)
  doc_coupling: skipped (--status-only, CI-validated)
commit: 6fa4f4a
```
**Priority:** Medium
**Created:** 2026-02-01
**Context:** Gemini review identified confusing terminology around LLM resources. Three constraints exist but names don't make their purposes clear.

---

## Problem

Current resource naming causes confusion:

| Current Name | Actual Purpose | Confusion |
|--------------|----------------|-----------|
| `llm_tokens` | Rate limit (tokens per window) | Sounds like token counting/budget |
| `llm_calls` | Rate limit (calls per window) | Inconsistent naming style |
| `llm_budget` | Total spend limit (dollars) | Unclear it's dollar-denominated |

Additionally:
- `resources.py` has a misleading deprecation note on `RESOURCE_LLM_TOKENS`
- No documentation explains the three-constraint model
- GLOSSARY.md lacks clear definitions

---

## Solution

### 1. Rename Resources (Config)

**Before:**
```yaml
rate_limiting:
  llm_tokens:           # Confusing: sounds like counting, actually rate limit
    max_per_window: 1000
  llm_calls:            # OK but inconsistent with llm_tokens naming
    max_per_window: 100

resources:
  stock:
    llm_budget:         # Unclear it's dollar-denominated
      total: 1.0
      unit: dollars
```

**After:**
```yaml
rate_limiting:
  llm_token_rate:            # Clear: rate limit on token consumption
    max_per_window: 1000
  llm_call_rate:             # Clear: rate limit on API calls
    max_per_window: 100

resources:
  stock:
    llm_dollar_budget:       # Clear: dollar-denominated total budget
      total: 1.0
```

### 2. Document Three-Constraint Model

Agents face THREE independent LLM constraints:

| Constraint | Type | Purpose | Exhaustion Effect |
|------------|------|---------|-------------------|
| `llm_token_rate` | Rate limit (renewable) | Controls token velocity | Temporary — wait for window |
| `llm_call_rate` | Rate limit (renewable) | Controls call frequency | Temporary — wait for window |
| `llm_dollar_budget` | Stock (depletable) | Controls total spend | Permanent — no more LLM calls |

**Why three?**
- Token rate prevents prompt-stuffing (huge prompts to game the system)
- Call rate prevents rapid-fire small calls (DoS-like behavior)
- Dollar budget provides economic constraint (scarcity drives emergence)

### 3. Update Code Constants

**`src/world/resources.py`:**
```python
# === Rate Limits (velocity constraints) ===

RESOURCE_LLM_TOKEN_RATE = "llm_token_rate"
"""Rate limit on LLM token consumption per window.
Controls velocity of token usage. Renewable — capacity replenishes."""

RESOURCE_LLM_CALL_RATE = "llm_call_rate"
"""Rate limit on LLM API calls per window.
Controls call frequency. Renewable — capacity replenishes."""

# === Budget (capacity constraint) ===

RESOURCE_LLM_DOLLAR_BUDGET = "llm_dollar_budget"
"""Total LLM spend limit in dollars.
Controls total capacity. Depletable — once spent, gone forever."""

# === Deprecated Aliases ===

RESOURCE_LLM_TOKENS = RESOURCE_LLM_TOKEN_RATE  # Deprecated
RESOURCE_LLM_BUDGET = RESOURCE_LLM_DOLLAR_BUDGET  # Deprecated
```

### 4. Update Config Schema

**`src/config_schema.py`:**
- Rename fields with backward compatibility
- Emit deprecation warnings for old names
- Update descriptions to be crystal clear

### 5. Add Documentation

**New section in `docs/architecture/current/resources.md`:**

```markdown
## LLM Resource Model

Agents face three independent constraints on LLM usage:

### Rate Limits (Velocity)

Rate limits control how FAST agents can use LLM resources:

| Limit | What it controls | Default | Recovery |
|-------|------------------|---------|----------|
| `llm_token_rate` | Tokens consumed per window | 1000/window | Wait for window to roll |
| `llm_call_rate` | API calls per window | 100/window | Wait for window to roll |

Rate limits are RENEWABLE — capacity replenishes as old usage falls outside the rolling window.

### Budget (Capacity)

Budget controls how MUCH total an agent can spend:

| Budget | What it controls | Default | Recovery |
|--------|------------------|---------|----------|
| `llm_dollar_budget` | Total dollar spend | $1.00 | None — permanent |

Budget is DEPLETABLE — once exhausted, the agent cannot make LLM calls.

### Interaction

An agent can hit any limit independently:
- High token velocity → token rate limited (temporary)
- High call frequency → call rate limited (temporary)
- Accumulated spend → budget exhausted (permanent)

This creates economic pressure: agents must balance speed vs cost.
```

**Update `docs/GLOSSARY.md`:**
```markdown
### llm_token_rate
Rate limit on LLM token consumption. Measured in tokens per rolling time window.
Renewable — capacity replenishes as old usage ages out.

### llm_call_rate
Rate limit on LLM API calls. Measured in calls per rolling time window.
Renewable — capacity replenishes as old usage ages out.

### llm_dollar_budget
Total dollar budget for LLM API costs. Depletable — once spent, gone forever.
Primary economic constraint driving agent behavior.
```

### 6. Fix Misleading Deprecation Note

Current `resources.py` says `RESOURCE_LLM_TOKENS` is deprecated but doesn't explain context. Update to:

```python
RESOURCE_LLM_TOKENS = RESOURCE_LLM_TOKEN_RATE
"""DEPRECATED: Renamed to RESOURCE_LLM_TOKEN_RATE for clarity.
This is a rate limit on tokens per window, not a token budget."""
```

---

## Migration

### Config Migration
- Accept both old and new names
- Emit deprecation warning if old names used
- Document migration in CHANGELOG

### Code Migration
- Update constant imports
- Update tests

---

## Files Changed

| File | Change |
|------|--------|
| `src/world/resources.py` | Rename constants, fix deprecation notes |
| `src/config_schema.py` | Rename fields, add backward compat |
| `config/config.yaml` | Use new names (optional, old still work) |
| `docs/architecture/current/resources.md` | Add three-constraint explanation |
| `docs/GLOSSARY.md` | Add/update definitions |
| `src/world/ledger.py` | Update internal references |
| `src/world/rate_tracker.py` | Update if needed |
| Tests | Update to use new names |

---

## Acceptance Criteria

- [ ] Config uses clear names (`llm_token_rate`, `llm_call_rate`, `llm_dollar_budget`)
- [ ] Old names still work with deprecation warning
- [ ] `resources.md` explains three-constraint model
- [ ] GLOSSARY.md has clear definitions
- [ ] Deprecation notes explain the rename (not removal)
- [ ] All tests pass

---

## Related

- Plan #166: Resource Rights Model (introduced llm_budget)
- Plan #247: Remove Legacy Tick-Based Resource Mode
- Gemini review finding (2026-02-01)
