# Plan #51: V1 Acceptance Criteria

**Status:** 📋 Planned
**Priority:** **High**
**Blocked By:** None
**Blocks:** V1 release confidence

---

## Gap

**Current:** No formal definition of what "V1" means. No automated verification that V1 works.

**Target:** Concrete V1 acceptance criteria with automated tests proving they pass.

**Why High:** Can't prove V1 works without this. "V1 complete" is guesswork.

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `docs/V1_ACCEPTANCE.md` | Define concrete V1 criteria |
| `tests/e2e/test_v1_acceptance.py` | Test each criterion |
| `.github/workflows/ci.yml` | CI job for V1 acceptance |

### Steps

1. **Draft V1 criteria** - Review README.md and architecture docs
2. **Create acceptance doc** - `docs/V1_ACCEPTANCE.md`
3. **Write acceptance tests** - `tests/e2e/test_v1_acceptance.py`
4. **Add CI job** - Run acceptance tests on main
5. **Verify all pass** - Ensure V1 criteria are met

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/e2e/test_v1_acceptance.py` | `test_ac_1_artifact_discovery` | Agents discover artifacts |
| `tests/e2e/test_v1_acceptance.py` | `test_ac_2_artifact_invocation` | Agents invoke interfaces |
| `tests/e2e/test_v1_acceptance.py` | `test_ac_3_scrip_transfers` | Ledger transfers work |
| `tests/e2e/test_v1_acceptance.py` | `test_ac_4_resource_constraints` | Rate limiting enforced |
| `tests/e2e/test_v1_acceptance.py` | `test_ac_5_contracts` | Contracts work |
| `tests/e2e/test_v1_acceptance.py` | `test_ac_6_escrow` | Escrow trading works |

---

## Acceptance Criteria

1. `docs/V1_ACCEPTANCE.md` exists with concrete criteria
2. `tests/e2e/test_v1_acceptance.py` tests each criterion
3. All V1 acceptance tests pass
4. CI runs acceptance tests on main branch

---

## Notes

Split from Plan #41 (Meta-Process Enforcement Gaps) Step 5. Plan #41 focused on enforcement tooling; this plan focuses on V1 product definition.

---

## References

- Plan #41: Meta-Process Enforcement Gaps (origin)
- README.md (project goals)
- docs/architecture/current/ (implementation status)
