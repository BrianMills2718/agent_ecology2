# Plan #242: Schema Audit Cleanup

**Status:** Planned
**Priority:** P1 (code bug) + P2 (doc consistency)
**Blocked By:** None
**Branch:** (pending)

## Context

Post-CMF-v3 audit (2026-01-31) found 24 issues across code and docs. One is a runtime crash (P0), several are src/ fixes needing tests, the rest are doc-only cleanups.

## Scope

### Phase 1: Code Bug Fix (requires tests)

| # | Severity | File | Issue |
|---|----------|------|-------|
| 1 | **HIGH** | `src/world/action_executor.py:979,1043,1146,1282` | `agent_artifact.artifact_type` → should be `agent_artifact.type`. Four handlers crash at runtime: subscribe, unsubscribe, configure_context, modify_system_prompt |

### Phase 2: src/ Comment/Docstring Fixes

| # | Severity | File | Issue |
|---|----------|------|-------|
| 3 | HIGH | `src/world/actions.py:14` | Docstring says "6 physics verbs" — should reflect 11 action types |
| 4 | HIGH | `src/world/actions.py:597` | `parse_intent` error message missing `configure_context` and `modify_system_prompt` |
| 9 | MEDIUM | `src/world/genesis_contracts.py:29` | Governance header says "Four" contracts — should be "Five" (+ `transferable_freeware`) |
| 18 | LOW | `src/world/ledger.py:21`, `src/world/world.py:201`, `src/world/genesis/rights_registry.py:28` | Reference non-existent `docs/RESOURCE_MODEL.md` → should be `docs/architecture/current/resources.md` |

### Phase 3: Doc-Only Fixes ([Trivial]-eligible, batched separately)

| # | Severity | File | Issue |
|---|----------|------|-------|
| 2 | HIGH | `docs/GLOSSARY.md:55-58` | Timestamp types: says `datetime`, code uses `str` |
| 5 | HIGH | `docs/CONCEPTUAL_MODEL.yaml:125` | Phantom `creator_only` genesis contract (code has 5 contracts, not 6) |
| 6 | HIGH | `docs/CONCEPTUAL_MODEL_FULL.yaml:357` | `modify_system_prompt` operations: `replace_section`/`reset` → `replace`/`remove`/`clear` |
| 7 | MEDIUM | `docs/CONCEPTUAL_MODEL_FULL.yaml:444` | KernelActions `method_count: 12` → should be 15, missing 3 charge delegation methods |
| 8 | MEDIUM | `CLAUDE.md` (root) | KernelActions table missing 4 methods |
| 10 | MEDIUM | `docs/architecture/current/contracts.md:94-99` | Missing `transferable_freeware` in genesis contracts table |
| 11 | MEDIUM | `docs/architecture/current/execution_model.md:28` | Phantom `is_memory=True` field → use `type="memory"` |
| 12 | MEDIUM | `docs/architecture/current/artifacts_executor.md:584-589` | Intent Types table lists 4 of 11 intents |
| 13 | MEDIUM | `docs/architecture/current/artifacts_executor.md:522` | "three narrow waist actions" → should be 11 |
| 14 | MEDIUM | `docs/architecture/current/execution_model.md:52` | Action categorization mismatch with CMF |
| 15 | MEDIUM | `docs/architecture/current/contracts.md:5` | Stale "Last verified" date (2026-01-23) |
| 16 | MEDIUM | `scripts/relationships.yaml:102` | Stale `src/world/genesis.py` → should be `src/world/genesis/__init__.py` or `factory.py` |
| 17 | MEDIUM | `docs/CONCEPTUAL_MODEL.yaml:97` | KernelActions says "12 methods" → 15 |

### Phase 4: Coupling Graph Fixes ([Trivial]-eligible)

| # | Severity | File | Issue |
|---|----------|------|-------|
| 20 | LOW | `scripts/relationships.yaml` | `kernel_interface.py` not in any doc-code coupling |
| 21 | LOW | `scripts/relationships.yaml` | `genesis_contracts.py` not coupled to `contracts.md` |
| 22 | LOW | `scripts/relationships.yaml:90` | Description says "Tick loop" — system uses autonomous mode |
| 9b | MEDIUM | `scripts/relationships.yaml:50` | Governance context says "Four" contracts → "Five" |

### Deferred (no action now)

| # | Severity | Issue | Why deferred |
|---|----------|-------|-------------|
| 19 | LOW | `relationships.yaml` lists legacy `doc_coupling.yaml` in CI coupling | Not broken, just legacy |
| 23 | LOW | 5 pending decisions in DC §13.2-13.6 | Intentionally open, need user judgment |
| 24 | LOW | `KernelState.list_artifacts_by_owner` wraps internal method with different name | Works, cosmetic |

## Implementation Strategy

1. **Phase 1 first** — Fix the runtime crash, add regression tests
2. **Phase 2** — Fix src/ comments/docstrings in same branch (saves a plan)
3. **Phase 3+4** — Batch all doc/config fixes in a `[Trivial]` commit on same branch

## Required Tests

- [ ] Test subscribe action succeeds (currently crashes on `artifact_type`)
- [ ] Test unsubscribe action succeeds
- [ ] Test configure_context action succeeds
- [ ] Test modify_system_prompt action succeeds
- [ ] Regression: verify `agent_artifact.type` is used, not `artifact_type`

## Acceptance Criteria

- [ ] All 4 crashing action handlers fixed and tested
- [ ] src/ docstrings/comments accurate
- [ ] Doc inconsistencies resolved (20 items)
- [ ] `make test` passes
- [ ] `make mypy` passes
- [ ] `make lint` passes
