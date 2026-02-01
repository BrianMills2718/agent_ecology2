# Plan #252: Tick Terminology Cleanup

**Status:** 📋 Planned
**Priority:** Low
**Created:** 2026-02-01
**Context:** Plan #247 removed tick-based execution mode, but ~77 references to "tick" remain in config schema and docs. Gemini review flagged this inconsistency.

---

## Problem

Plan #247 removed the legacy tick-based resource mode, making autonomous loops the only execution model. However, terminology cleanup was incomplete:

- `config_schema.py` still has `checkpoint_interval` described as "every N ticks"
- `config_schema.py` has `first_tick_hint`, `first_tick_enabled`, `trend_history_ticks`
- Docs reference "ticks" in various places
- GLOSSARY.md may have outdated definitions

This creates confusion: new readers see "tick" references but ticks no longer exist.

---

## Solution

### 1. Audit All References

```bash
grep -rn "tick" src/config_schema.py docs/ --include="*.md" --include="*.yaml"
```

### 2. Categorize References

| Category | Action |
|----------|--------|
| Config field names | Rename if feasible, or document as legacy |
| Config descriptions | Update to reflect autonomous model |
| Doc explanations | Rewrite for autonomous model |
| GLOSSARY entries | Update or remove |

### 3. Rename Config Fields (if feasible)

| Current | Proposed | Notes |
|---------|----------|-------|
| `checkpoint_interval` | Keep name, fix description | "Every N events" not "ticks" |
| `first_tick_hint` | `startup_hint` | Shown on first iteration |
| `first_tick_enabled` | `startup_hint_enabled` | |
| `trend_history_ticks` | `trend_history_events` | |

### 4. Update Descriptions

**Before:**
```python
checkpoint_interval: int = Field(
    description="Save checkpoint every N ticks (0 = disable periodic saves)"
)
```

**After:**
```python
checkpoint_interval: int = Field(
    description="Save checkpoint every N events (0 = disable periodic saves)"
)
```

### 5. Update Docs

Files to review:
- `docs/architecture/current/execution_model.md`
- `docs/architecture/current/supporting_systems.md`
- `docs/GLOSSARY.md`
- Any other docs referencing "tick"

---

## Migration

- Config field renames need backward compatibility
- Accept old names with deprecation warning
- Document in CHANGELOG

---

## Files Changed

| File | Change |
|------|--------|
| `src/config_schema.py` | Rename fields, update descriptions |
| `docs/architecture/current/execution_model.md` | Remove tick references |
| `docs/architecture/current/supporting_systems.md` | Update checkpoint description |
| `docs/GLOSSARY.md` | Update/remove tick entry |
| Other docs | As identified in audit |

---

## Acceptance Criteria

- [ ] No "tick" in config descriptions (except explicitly deprecated)
- [ ] Docs describe autonomous model, not tick-based
- [ ] GLOSSARY updated
- [ ] Old config names still work (backward compat)

---

## Related

- Plan #247: Remove Legacy Tick-Based Resource Mode
- Plan #102: Duration-based execution (removed max_ticks)
- Gemini review finding (2026-02-01)
