# Plan 178: Configurable Enforcement Strictness

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** None
**Blocks:** None

---

## Gap

**Current:**
1. `sync_plan_status.py --sync` only updates existing index rows, doesn't add new plans
2. Soft doc couplings warn but don't fail CI - allows drift to accumulate
3. No configuration for enforcement levels - strictness is hardcoded

**Target:**
1. `--sync` adds missing plans to index automatically
2. All couplings strict by default
3. Configurable via `meta-process.yaml` with warnings when downgrading

**Why High:** These enforcement gaps allow drift to accumulate silently. 57 plans currently missing from index.

---

## References Reviewed

- `scripts/sync_plan_status.py:269-339` - Current sync only updates, doesn't add
- `scripts/doc_coupling.yaml` - Current coupling config with soft: true options
- `scripts/check_doc_coupling.py` - Coupling enforcement logic
- `.claude/meta-config.yaml` - Existing meta config (if exists)

---

## Files Affected

- `scripts/sync_plan_status.py` (modify) - Add new plans to index
- `scripts/check_doc_coupling.py` (modify) - Read strictness from config
- `scripts/doc_coupling.yaml` (modify) - Add deprecation warning comment
- `meta-process.yaml` (create) - Configurable enforcement settings
- `CLAUDE.md` (modify) - Document new config options
- `.claude/hooks/protect-main.sh` (modify) - Support atomic claims
- `.claude/hooks/block-worktree-remove.sh` (modify) - Support atomic claims
- `tests/scripts/test_sync_plan_status.py` (create) - Tests for sync functionality
- `tests/scripts/test_doc_coupling.py` (create) - Tests for coupling strictness

---

## Plan

### Configuration Schema

Create `meta-process.yaml` in repo root:
```yaml
# Meta-Process Configuration
#
# WARNING: Reducing enforcement strictness allows drift to accumulate.
# Only downgrade strictness if you have alternative enforcement mechanisms.

enforcement:
  # Plan index sync: automatically add new plans to docs/plans/CLAUDE.md
  plan_index_auto_add: true  # Default: true

  # Doc-code coupling: fail CI on any coupling violation
  # Set to false to allow soft couplings (NOT RECOMMENDED)
  # If false, soft couplings in doc_coupling.yaml will warn instead of fail
  strict_doc_coupling: true  # Default: true

  # When strict_doc_coupling is false, this warning is shown on every CI run
  show_strictness_warning: true
```

### Changes Required

| File | Change |
|------|--------|
| `scripts/sync_plan_status.py` | Add `add_missing_to_index()` function, call from `--sync` |
| `scripts/check_doc_coupling.py` | Read `strict_doc_coupling` from config, apply to soft couplings |
| `scripts/doc_coupling.yaml` | Add warning comment, note that soft is deprecated |
| `meta-process.yaml` | Create with defaults and warning comments |
| `CLAUDE.md` | Document configuration options |

### Steps

1. **Create `meta-process.yaml`** with default strict settings
   - Include prominent warnings about downgrading
   - Document each setting

2. **Update `sync_plan_status.py`**
   - Add function to find plans not in index
   - Generate index row from plan file metadata
   - Insert at correct position (sorted by number)
   - Make configurable via `plan_index_auto_add`

3. **Update `check_doc_coupling.py`**
   - Load `meta-process.yaml` config
   - If `strict_doc_coupling: true`, treat soft couplings as strict
   - If `strict_doc_coupling: false`, show warning on every run

4. **Update `doc_coupling.yaml`**
   - Add deprecation warning for `soft: true`
   - Note that behavior depends on `strict_doc_coupling` config

5. **Update CLAUDE.md**
   - Document `meta-process.yaml` configuration
   - Explain enforcement levels

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_sync_plan_status.py` | `test_adds_missing_plans_to_index` | New plans added to index |
| `tests/test_doc_coupling.py` | `test_strict_mode_fails_soft_couplings` | Soft couplings fail when strict |
| `tests/test_doc_coupling.py` | `test_shows_warning_when_not_strict` | Warning shown on downgrade |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_*.py` | Full suite regression |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Sync adds new plans | Create plan file, run `--sync` | Plan appears in index |
| Strict mode fails soft | Set strict: true, violate soft coupling | CI fails |
| Warning on downgrade | Set strict: false, run coupling check | Warning displayed |

---

## Verification

### Tests & Quality
- [ ] All required tests pass
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/`

### Documentation
- [ ] CLAUDE.md updated with config options
- [ ] meta-process.yaml has clear warnings

### Completion Ceremony
- [ ] Plan file status -> `Complete`
- [ ] `plans/CLAUDE.md` index -> `Complete`
- [ ] Branch merged or PR created

---

## Notes

### Why Strict by Default?

Soft couplings were added to avoid blocking work, but they allow drift to accumulate.
The 57 missing plans in the index are proof of this. Better to be strict and allow
explicit configuration to downgrade, with warnings.

### Backwards Compatibility

Existing `soft: true` in `doc_coupling.yaml` will be respected when `strict_doc_coupling: false`.
When `strict_doc_coupling: true` (default), all couplings are treated as strict regardless
of the `soft` flag.
