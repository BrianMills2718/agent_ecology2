# Plan 231: Tight Coupling Between has_standing and Ledger Registration

**Status:** 📋 Planned
**Priority:** Medium
**Blocked By:** -
**Blocks:** -

---

## Gap

**Current:** `artifact.has_standing` and ledger registration are independent:
- An artifact can have `has_standing=True` without being in the ledger
- The runner tries to sync them but they can diverge
- This creates contradictory states ("can hold resources" but has no ledger entry)

**Target:** Kernel invariant: `has_standing=True` ↔ registered in ledger. They are always in sync.

**Why Medium:** Inconsistency is confusing but current best-effort sync mostly works.

---

## References Reviewed

- `src/world/artifacts.py:166` - `has_standing: bool = False`
- `src/world/ledger.py:180-200` - `create_principal()` creates ledger entry
- `src/simulation/runner.py:453-460` - Runner syncs ledger→artifact
- `src/world/kernel_interface.py:635-661` - `create_principal()` kernel primitive
- `docs/CONCEPTUAL_MODEL.yaml` - `has_standing` definition

---

## Open Questions

### Before Planning

1. [ ] **Question:** Should setting `has_standing=True` on artifact auto-create ledger entry?
   - **Status:** ❓ OPEN
   - **Why it matters:** Determines where the coupling is enforced

2. [ ] **Question:** Should `create_principal()` also set artifact `has_standing=True`?
   - **Status:** ❓ OPEN
   - **Why it matters:** Determines single point of truth

3. [ ] **Question:** What happens on checkpoint restore if artifact has `has_standing` but ledger doesn't have entry yet?
   - **Status:** ❓ OPEN
   - **Why it matters:** Order of operations during restore

---

## Design Options

### Option A: Artifact-driven
Setting `artifact.has_standing = True` auto-creates ledger entry with 0 balance.

**Pros:** Single operation to make something a principal
**Cons:** Artifact store needs ledger reference, coupling

### Option B: Ledger-driven (Recommended)
`create_principal()` is the ONLY way to create a principal. It:
1. Creates ledger entry
2. If artifact exists, sets `has_standing=True`
3. If artifact doesn't exist, creates it with `has_standing=True`

**Pros:** Single source of truth (ledger), clear responsibility
**Cons:** Can't create artifact with standing without ledger call

### Option C: Kernel primitive creates both atomically
New kernel primitive `create_standing_artifact()` that creates both in one call.

**Pros:** Atomic, clear semantics
**Cons:** New primitive needed

---

## Tradeoffs

| Aspect | Loose (current) | Tight (proposed) |
|--------|-----------------|------------------|
| Mental model | Complex | Simple |
| Contradictions | Possible | Impossible |
| Checkpoint restore | Flexible | Need care |
| Code coupling | Low | Higher |
| Failure modes | Silent drift | Explicit failure |

---

## Files Affected

TBD based on design option chosen.

Likely:
- `src/world/kernel_interface.py` (modify)
- `src/world/artifacts.py` (modify)
- `src/world/ledger.py` (modify)
- `src/simulation/runner.py` (modify)
- `src/simulation/checkpoint.py` (modify)

---

## Plan

TBD after design option is chosen.

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/unit/test_standing_invariant.py` | `test_has_standing_implies_ledger_entry` | Invariant holds |
| `tests/unit/test_standing_invariant.py` | `test_create_principal_sets_has_standing` | Both set together |
| `tests/unit/test_standing_invariant.py` | `test_checkpoint_restore_maintains_invariant` | Restore is correct |

---

## Verification

### Tests & Quality
- [ ] Invariant tests pass
- [ ] Checkpoint round-trip maintains invariant
- [ ] No contradictory states possible

### Documentation
- [ ] Conceptual model updated to document invariant
- [ ] Glossary clarifies relationship

---

## Notes

This is a design decision that needs discussion. The current loose coupling works but creates potential for confusion. Tight coupling is simpler conceptually but requires more careful implementation.

Recommend: Start with Option B (ledger-driven) as it has clearest single source of truth.
