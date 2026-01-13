# Gap 34: Oracle to Mint Rename

**Status:** ✅ Complete (PR #46 merged)
**Priority:** Medium
**Blocked By:** -
**Blocks:** -
**ADR:** [ADR-0004](../adr/0004-mint-system-primitive.md)

---

## Gap

**Current:** The codebase uses "oracle" terminology throughout:
- `GenesisOracle` class in `src/world/genesis.py`
- `OracleScorer` class in `src/world/oracle_scorer.py`
- Config keys: `genesis.oracle.*`
- 34+ files reference "oracle"

**Target:** All code and config uses "mint" terminology:
- `GenesisMint` class
- `MintScorer` class
- Config keys: `genesis.mint.*`
- Documentation already updated (ADR-0004, GLOSSARY.md, target architecture)

**Why Medium:**
- Pure refactoring, no behavioral change
- Docs already updated, creating drift between code and docs
- Not blocking other work
- Should be done before external visibility increases

---

## Plan

### Changes Required

| File | Change |
|------|--------|
| `src/world/genesis.py` | Rename `GenesisOracle` → `GenesisMint` |
| `src/world/oracle_scorer.py` | Rename file to `mint_scorer.py`, class to `MintScorer` |
| `config/config.yaml` | Rename `genesis.oracle` → `genesis.mint` |
| `config/schema.yaml` | Rename oracle schema section → mint |
| `src/config.py` | Update any oracle references |
| `src/simulation/runner.py` | Update oracle → mint references |
| `tests/*.py` | Update all test references |
| `docs/architecture/current/oracle.md` | Rename to `mint.md`, update content |
| `docs/architecture/current/*.md` | Update references |

### Steps

1. **Rename core files:**
   - `src/world/oracle_scorer.py` → `src/world/mint_scorer.py`
   - Update imports everywhere

2. **Rename classes:**
   - `GenesisOracle` → `GenesisMint`
   - `OracleScorer` → `MintScorer`
   - `OraclePhase` → `MintPhase` (if exists)

3. **Update config:**
   - Rename all `oracle` keys to `mint` in `config.yaml`
   - Update `schema.yaml` accordingly
   - Update `get_genesis_config("oracle", ...)` calls → `get_genesis_config("mint", ...)`

4. **Update tests:**
   - Rename test files if any are oracle-specific
   - Update all oracle references in assertions, fixtures, etc.

5. **Update current architecture docs:**
   - Rename `docs/architecture/current/oracle.md` → `mint.md`
   - Update all internal references
   - Remove deprecation note (now accurate)

6. **Verify no oracle references remain:**
   ```bash
   grep -ri "oracle" src/ config/ tests/ docs/architecture/current/ --include="*.py" --include="*.yaml" --include="*.md"
   ```

---

## Required Tests

### Existing Tests (Must Pass)

All existing oracle-related tests must pass after renaming:

| Test Pattern | Why |
|--------------|-----|
| `tests/unit/test_genesis_contracts.py` | Genesis contracts still work |
| `tests/integration/test_genesis_store.py` | Genesis store still works |
| `tests/integration/test_mint_auction.py` | Scoring/minting still works (renamed from test_oracle_auction.py) |
| `tests/integration/test_runner.py` | Integration unchanged |

### Verification Tests

After refactoring, verify:

| Test | What It Verifies |
|------|------------------|
| `pytest tests/` | All tests pass |
| No "oracle" in grep | Terminology fully migrated |
| Config loading works | Schema/config in sync |

---

## Verification

### Tests & Quality
- [ ] All tests pass: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`
- [ ] No "oracle" references in code: `grep -ri oracle src/ config/ --include="*.py" --include="*.yaml"`

### Documentation
- [x] `docs/architecture/current/oracle.md` → `mint.md`
- [x] All current/ docs updated (genesis_artifacts.md, configuration.md, running.md, supporting_systems.md)
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Claim released from Active Work table (root CLAUDE.md)
- [ ] Branch merged or PR created

---

## Notes

- ADR-0004 documents the rationale for this change
- GLOSSARY.md and target architecture already updated
- This is a mechanical refactoring - no behavioral changes
- Consider doing in a single atomic commit for easy revert if needed
