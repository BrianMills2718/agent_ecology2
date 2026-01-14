# Plan #51: V1 Acceptance Criteria

**Status:** ✅ Complete

**Verified:** 2026-01-14T22:26:36Z
**Verification Evidence:**
```yaml
completed_by: scripts/complete_plan.py
timestamp: 2026-01-14T22:26:36Z
tests:
  unit: 1340 passed, 7 skipped in 16.88s
  e2e_smoke: PASSED (2.07s)
  e2e_real: PASSED (4.31s)
  doc_coupling: passed
commit: f750ce0
```

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
| `tests/e2e/test_v1_acceptance.py` | `TestV1MultiAgentExecution::test_multi_agent_execution` | Multiple agents run without interference |
| `tests/e2e/test_v1_acceptance.py` | `TestV1ArtifactSystem::test_artifact_discovery` | Agents can discover artifacts via genesis_store |
| `tests/e2e/test_v1_acceptance.py` | `TestV1ArtifactSystem::test_artifact_creation` | Agents can create new artifacts |
| `tests/e2e/test_v1_acceptance.py` | `TestV1ArtifactSystem::test_artifact_invocation` | Agents can invoke artifact interfaces |
| `tests/e2e/test_v1_acceptance.py` | `TestV1EconomicPrimitives::test_scrip_transfer` | Ledger transfers work correctly |
| `tests/e2e/test_v1_acceptance.py` | `TestV1ResourceConstraints::test_resource_rate_limiting` | Rate limits are enforced |
| `tests/e2e/test_v1_acceptance.py` | `TestV1Coordination::test_escrow_coordination` | Escrow enables trustless artifact trade |
| `tests/e2e/test_v1_acceptance.py` | `TestV1Observability::test_action_logging` | All actions are logged to event log |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/e2e/test_smoke.py` | Smoke tests still work |
| `tests/e2e/test_real_e2e.py` | Real E2E still works |

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
