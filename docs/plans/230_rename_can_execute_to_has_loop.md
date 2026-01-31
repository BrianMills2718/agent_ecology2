# Plan 230: Rename can_execute to has_loop

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** Code uses `can_execute` for "can execute autonomously (has own loop)" but this is confusingly similar to `executable` (can be invoked). The conceptual model uses `has_loop` which is clearer.

**Target:** Consistent terminology: `has_loop` everywhere (code, docs, conceptual model).

**Why Medium:** Terminology inconsistency causes confusion but doesn't block functionality.

---

## References Reviewed

- `src/world/artifacts.py:167` - `can_execute: bool = False` definition
- `src/world/artifacts.py:219-228` - `is_agent` property uses `can_execute`
- `src/simulation/runner.py` - Uses `can_execute` in checkpoint restore
- `docs/CONCEPTUAL_MODEL.yaml` - Uses `has_loop`
- `docs/GLOSSARY.md:57` - Documents `can_execute`

---

## Open Questions

### Resolved

1. [x] **Question:** How many occurrences need to change?
   - **Status:** ✅ RESOLVED
   - **Answer:** 68 total (19 in src/, 49 in tests/)
   - **Verified in:** grep search during Plan #229

2. [x] **Question:** Is this a breaking change?
   - **Status:** ✅ RESOLVED
   - **Answer:** Yes for checkpoint files that contain `can_execute`. Need migration.
   - **Verified in:** `src/simulation/runner.py:292-295`

---

## Files Affected

- `src/world/artifacts.py` (modify - 12 occurrences)
- `src/simulation/runner.py` (modify - 5 occurrences)
- `src/agents/agent.py` (modify - 1 occurrence)
- `src/agents/_handbook/self.md` (modify - 1 occurrence)
- `tests/integration/test_unified_ontology.py` (modify - 8 occurrences)
- `tests/unit/test_agent_artifacts.py` (modify - 34 occurrences)
- `tests/unit/test_artifact_memory_checkpoint.py` (modify - 2 occurrences)
- `tests/unit/test_agent_rights.py` (modify - 3 occurrences)
- `tests/unit/test_workflow.py` (modify - 2 occurrences)
- `docs/GLOSSARY.md` (modify)
- `docs/architecture/current/*.md` (modify as needed)

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/artifacts.py` | Rename field `can_execute` → `has_loop` |
| All test files | Update references |
| Checkpoint restore | Support both `can_execute` and `has_loop` for migration |
| Glossary | Update property definition |

### Steps

1. Add `has_loop` as alias in Artifact dataclass (backward compat)
2. Update `is_agent` property to use `has_loop`
3. Update all test files
4. Update runner checkpoint restore to read both fields
5. Update glossary and docs
6. Remove `can_execute` alias after confirming no external dependencies

---

## Required Tests

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_agent_artifacts.py` | Agent creation unchanged |
| `tests/integration/test_unified_ontology.py` | Ontology unchanged |

---

## Verification

### Tests & Quality
- [ ] All tests pass after rename
- [ ] Type check passes
- [ ] Checkpoint migration works (old files load correctly)

### Documentation
- [ ] Glossary updated
- [ ] Conceptual model consistent
- [ ] Architecture docs updated

---

## Notes

This is a mechanical refactor. The key complexity is checkpoint backward compatibility - need to support loading old checkpoints that use `can_execute`.
