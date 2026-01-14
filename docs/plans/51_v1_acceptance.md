# Plan #51: V1 Acceptance Criteria

**Status:** 📋 Planned

**Priority:** **High**
**Blocked By:** None (extracted from #41)
**Blocks:** V1 release declaration

---

## Gap

**Current:** We have smoke tests and basic real E2E tests, but no formal definition of what "V1" means. Can't prove V1 works because we haven't defined V1.

**Target:** Clear V1 acceptance criteria with comprehensive E2E tests that validate all core features work end-to-end with real LLM.

**Why High:** Without V1 acceptance criteria, "V1 complete" is guesswork. This blocks confident release declaration.

---

## V1 Definition

V1 is the **minimal viable agent ecology** - sufficient to demonstrate emergent collective capability under resource constraints.

### Core Capabilities (Must Have)

1. **Multi-Agent Execution** - Multiple agents run simultaneously without interference
2. **Artifact System** - Agents can discover, create, read, and invoke artifacts
3. **Economic Primitives** - Scrip transfers work, balances are tracked correctly
4. **Resource Constraints** - Rate limiting and quotas are enforced
5. **Coordination** - Contracts and escrow enable trustless coordination
6. **Observability** - Actions are logged and traceable

### Not in V1 (Explicitly Excluded)

- Agent rights trading (Plan #8)
- Scrip debt contracts (Plan #9)
- Memory persistence (Plan #10)
- Library installation (Plan #29)
- LLM budget trading (Plan #30)

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `docs/V1_ACCEPTANCE.md` | Create V1 acceptance criteria document |
| `tests/e2e/test_v1_acceptance.py` | Create comprehensive V1 acceptance tests |
| `.github/workflows/ci.yml` | Add V1 acceptance job (optional) |

### Steps

1. Create `docs/V1_ACCEPTANCE.md` with formal criteria
2. Create `tests/e2e/test_v1_acceptance.py` with tests for each criterion
3. Verify all tests pass with `--run-external`
4. Update CI to run V1 acceptance on release branches (optional)

---

## Required Tests

### New Tests (TDD)

Create these tests FIRST, before implementing:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/e2e/test_v1_acceptance.py` | `test_multi_agent_execution` | Multiple agents run without interference |
| `tests/e2e/test_v1_acceptance.py` | `test_artifact_discovery` | Agents can discover artifacts via genesis_store |
| `tests/e2e/test_v1_acceptance.py` | `test_artifact_creation` | Agents can create new artifacts |
| `tests/e2e/test_v1_acceptance.py` | `test_artifact_invocation` | Agents can invoke artifact interfaces |
| `tests/e2e/test_v1_acceptance.py` | `test_scrip_transfer` | Ledger transfers work correctly |
| `tests/e2e/test_v1_acceptance.py` | `test_resource_rate_limiting` | Rate limits are enforced |
| `tests/e2e/test_v1_acceptance.py` | `test_escrow_coordination` | Escrow enables trustless artifact trade |
| `tests/e2e/test_v1_acceptance.py` | `test_action_logging` | All actions are logged to event log |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/e2e/test_smoke.py` | Smoke tests still work |
| `tests/e2e/test_real_e2e.py` | Real E2E still works |

---

## E2E Verification

**Required:** All V1 acceptance tests must pass with real LLM.

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Multi-agent economy | 1. Run 3 agents for 5 ticks | All agents execute, balances tracked |
| Artifact lifecycle | 1. Agent discovers store 2. Creates artifact 3. Another agent invokes | Artifact created and invocable |
| Economic transaction | 1. Agent A transfers to Agent B | Balance correctly updated |

```bash
# Run V1 acceptance verification
pytest tests/e2e/test_v1_acceptance.py -v --run-external
```

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 51`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] **E2E verification passes:** `pytest tests/e2e/test_v1_acceptance.py -v --run-external`

### Documentation
- [ ] `docs/V1_ACCEPTANCE.md` created with clear criteria
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

This plan was extracted from Plan #41 Step 5 to give V1 acceptance proper scope and attention.

**Design decisions:**
- Tests use real LLM (`--run-external`) because V1 must work end-to-end
- Tests are comprehensive but not exhaustive - focus on core capabilities
- V1 scope is intentionally minimal - better to ship something that works

**Relationship to Plan #41:**
- Plan #41 focused on meta-process enforcement gaps
- V1 acceptance was one of those gaps but deserved its own plan
- Plan #41 can be completed once this plan is created (not necessarily complete)
