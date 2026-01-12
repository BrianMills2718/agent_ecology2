# Gap 6: Unified Artifact Ontology

**Status:** ✅ Complete
**Priority:** Medium
**Blocked By:** None
**Blocks:** #7, #8, #14, #16

---

## Gap

**Current:** Partial implementation - the artifact model supports unified ontology (`has_standing`, `can_execute`, `is_agent`, `is_principal` properties exist) but `SimulationRunner` creates agents directly without artifact backing.

**Target:** Everything is an artifact with properties. Agents are artifacts where `has_standing=True` AND `can_execute=True`. All agents are artifact-backed by default.

**Why Medium:** This is foundational for agent trading (#8), single ID namespace (#7), MCP interface (#14), and artifact discovery (#16). Once implemented, agents become first-class tradeable entities.

---

## Current State Analysis

### Already Implemented ✅
1. `Artifact` class has `has_standing`, `can_execute` fields (artifacts.py:125-127)
2. `is_principal` and `is_agent` properties on Artifact (artifacts.py:139-165)
3. `create_agent_artifact()` factory function (artifacts.py:261-335)
4. `create_memory_artifact()` factory function (artifacts.py:338-402)
5. `Agent.from_artifact()` and `Agent.to_artifact()` methods (agent.py:241-325)
6. `create_agent_artifacts()` in loader.py (loader.py:146-212)
7. `load_agents_from_store()` in loader.py (loader.py:215-253)

### Missing ❌
1. `SimulationRunner._create_agents()` creates agents WITHOUT artifact backing
2. `SimulationRunner._check_for_new_principals()` creates spawned agents WITHOUT artifact backing
3. No tests verifying artifact-backed agent behavior in simulation
4. Documentation says "Needs Plan" but implementation is 80% complete

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/simulation/runner.py` | Use `create_agent_artifacts()` + `load_agents_from_store()` in `__init__` |
| `src/simulation/runner.py` | Update `_check_for_new_principals()` to create artifact-backed agents |
| `docs/architecture/current/agents.md` | Document artifact-backed agents as default |
| `docs/plans/CLAUDE.md` | Update status to Complete |

### Steps

1. **Update SimulationRunner initialization:**
   - After world creation, call `create_agent_artifacts(world.artifacts, agent_configs)`
   - Replace `_create_agents()` call with `load_agents_from_store(world.artifacts)`
   - Ensure checkpoint restore works with artifact-backed agents

2. **Update dynamic agent creation:**
   - Modify `_check_for_new_principals()` to create agent artifacts for spawned principals
   - Use `create_agent_artifact()` instead of direct `Agent()` construction

3. **Handle checkpoint restore:**
   - Ensure restored artifacts include agent artifacts
   - Load agents from restored store after checkpoint restore

4. **Backward compatibility:**
   - Keep `Agent.__init__()` working for tests that create agents directly
   - Artifact backing is the default, but non-backed agents still function

---

## Required Tests

### New Tests (TDD)

Create these tests FIRST, before implementing:

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_unified_ontology.py` | `TestRunnerCreatesAgentArtifacts::test_runner_creates_agent_artifacts` | SimulationRunner populates artifact store with agent artifacts |
| `tests/test_unified_ontology.py` | `TestAgentsAreArtifactBacked::test_agents_are_artifact_backed` | All agents from runner have `is_artifact_backed=True` |
| `tests/test_unified_ontology.py` | `TestAgentArtifactProperties::test_agent_artifacts_have_correct_properties` | Agent artifacts have `has_standing=True`, `can_execute=True` |
| `tests/test_unified_ontology.py` | `TestMemoryArtifactsCreated::test_memory_artifacts_created` | Each agent has a linked memory artifact |
| `tests/test_unified_ontology.py` | `TestSpawnedAgentsArtifactBacked::test_spawned_agents_are_artifact_backed` | Dynamically created agents are also artifact-backed |
| `tests/test_unified_ontology.py` | `TestCheckpointPreservesAgentArtifacts::test_checkpoint_preserves_agent_artifacts` | Checkpoint save/restore maintains agent artifacts |

### Existing Tests (Must Pass)

These tests must still pass after changes:

| Test Pattern | Why |
|--------------|-----|
| `tests/test_runner.py` | Runner behavior unchanged |
| `tests/test_loader.py` | Agent loading still works |
| `tests/test_checkpoint.py` | Checkpoint round-trip preserved |
| `tests/test_async_agent.py` | Agent behavior unchanged |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 6`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] `docs/architecture/current/agents.md` updated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`
- [ ] Agent artifacts documented as default behavior

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

The infrastructure for artifact-backed agents already exists. This gap is primarily about:
1. Wiring it up as the default in SimulationRunner
2. Adding tests to verify the behavior
3. Updating documentation

This is lower risk than it appears because:
- The `Agent` class already supports both backed and non-backed modes
- Existing tests mostly create agents directly (will continue to work)
- The change is additive, not breaking
