# Plan 289: Complete Context Provision System

**Status:** 🚧 In Progress
**Priority:** High
**Blocked By:** #288 (foundation)
**Blocks:** -

---

## Gap

**Current:** Plan #288 injects context before edits, but:
1. Governance mappings in `relationships.yaml` are incomplete (ADR-0016 discusses "owner" but isn't mapped to artifacts.py)
2. No way to discover IMPLICIT relationships between docs and code
3. "Docs to check" is based on CI couplings, not actual relevance
4. Only shows doc references, not actual content when needed

**Target:** Complete context provision that:
1. Has COMPLETE manual mappings (every ADR mapped to all relevant files)
2. Has SEMANTIC SEARCH to find relevant docs even without explicit mappings
3. Injects actual content when critical (not just references)
4. Validates mapping completeness

**Why High:** Without complete context, Claude makes changes that violate ADRs, use forbidden terminology, or miss relevant design decisions. The current system gives false confidence - "context exists" ≠ "context is used".

---

## References Reviewed

- `scripts/relationships.yaml` - Current governance and coupling mappings
- `docs/adr/*.md` - All ADRs (need to audit for complete mappings)
- `docs/CONCEPTUAL_MODEL.yaml` - Entity definitions including non_existence
- `docs/GLOSSARY.md` - Terminology definitions
- `scripts/extract_relevant_context.py` - Plan #288 extraction script
- `.claude/hooks/inject-edit-context.sh` - Plan #288 hook

---

## Open Questions

### Before Planning

1. [x] **Question:** How many ADRs exist and how many have governance mappings?
   - **Status:** ✅ RESOLVED
   - **Answer:** Need to audit - will count in Phase 1
   - **Why it matters:** Determines scope of manual mapping work

2. [x] **Question:** What semantic search approach to use?
   - **Status:** ✅ RESOLVED
   - **Answer:** Start with BM25/TF-IDF (no dependencies, fast, effective). Upgrade to embeddings only if needed.
   - **Why it matters:** Affects implementation complexity

3. [ ] **Question:** Should semantic search run on every edit or be cached?
   - **Status:** ❓ OPEN
   - **Why it matters:** Performance vs freshness tradeoff

---

## Files Affected

### Phase 1: Complete Manual Mappings
- `scripts/relationships.yaml` (modify - add missing governance mappings)
- `scripts/audit_governance_mappings.py` (create - validates completeness)

### Phase 2: Semantic Search
- `scripts/build_doc_index.py` (create - builds searchable index of all docs)
- `scripts/semantic_doc_search.py` (create - BM25 search over docs)
- `scripts/extract_relevant_context.py` (modify - integrate semantic search)
- `data/doc_index.json` (create - cached document index)

### Phase 3: Validation
- `scripts/check_governance_completeness.py` (create - CI check for mapping coverage)

---

## Plan

### Phase 1: Audit and Complete Manual Mappings

1. **Audit current state:**
   - Count all ADRs
   - Count ADRs with governance mappings
   - Identify ADRs with NO mappings
   - Identify source files with NO governance

2. **Create audit script** (`audit_governance_mappings.py`):
   - List all ADRs
   - List all src/ files
   - Show coverage matrix
   - Flag unmapped ADRs and ungoverned files

3. **Complete mappings:**
   - Read each unmapped ADR
   - Determine which source files it governs
   - Add to relationships.yaml

4. **Add CONCEPTUAL_MODEL → source mappings:**
   - Map each entity (Artifact, Principal, Contract, etc.) to implementing files
   - Map non_existence terms to files where they appear (for warnings)

### Phase 2: Semantic Search

1. **Build document index** (`build_doc_index.py`):
   - Parse all ADRs, extract title + principles + content
   - Parse GLOSSARY.md, extract each term + definition
   - Parse CONCEPTUAL_MODEL.yaml, extract each entity + fields
   - Parse architecture docs
   - Store as JSON with BM25-ready tokenization

2. **Implement search** (`semantic_doc_search.py`):
   - Load index
   - Given a query (file content, extracted terms), find top-N relevant docs
   - Return ranked list with relevance scores
   - Use rank-bm25 library (pip install rank-bm25)

3. **Integrate into extraction** (modify `extract_relevant_context.py`):
   - After explicit mapping lookup, also run semantic search
   - Merge results (explicit mappings + semantic matches)
   - Deduplicate and rank

### Phase 3: Validation

1. **Create CI check** (`check_governance_completeness.py`):
   - Every ADR must have at least one governance mapping
   - Every src/ file should have governance (warning, not error)
   - CONCEPTUAL_MODEL entities should have source mappings

2. **Add to pre-commit** (optional):
   - Warn if adding src/ file without governance

---

## Required Tests

### New Tests (TDD)

| Test File | Test Function | What It Verifies |
|-----------|---------------|------------------|
| `tests/test_audit_governance.py` | `test_finds_unmapped_adrs` | Detects ADRs with no governance |
| `tests/test_audit_governance.py` | `test_finds_ungoverned_files` | Detects src files with no ADR |
| `tests/test_semantic_search.py` | `test_bm25_finds_relevant_doc` | Search finds relevant doc given terms |
| `tests/test_semantic_search.py` | `test_search_ranks_explicit_higher` | Explicit mappings rank above semantic |

### Existing Tests (Must Pass)

| Test Pattern | Why |
|--------------|-----|
| `tests/test_extract_context.py` | Plan #288 functionality preserved |

---

## E2E Verification

| Scenario | Steps | Expected Outcome |
|----------|-------|------------------|
| Edit artifacts.py | 1. Edit src/world/artifacts.py 2. Check injected context | Shows ADR-0001 AND ADR-0016 (semantic match for "owner") |
| Edit new file | 1. Create new src file 2. Edit it | Semantic search finds relevant docs even with no explicit mapping |

---

## Verification

### Tests & Quality
- [ ] All required tests pass: `python scripts/check_plan_tests.py --plan 289`
- [ ] Full test suite passes: `pytest tests/`
- [ ] Type check passes: `python -m mypy src/ --ignore-missing-imports`

### Documentation
- [ ] relationships.yaml fully populated
- [ ] Doc-coupling check passes: `python scripts/check_doc_coupling.py`

### Completion Ceremony
- [ ] Plan file status → `✅ Complete`
- [ ] `plans/CLAUDE.md` index → `✅ Complete`
- [ ] Branch merged or PR created

---

## Uncertainties

| Question | Status | Resolution |
|----------|--------|------------|
| BM25 vs embeddings performance | ❓ Open | Start with BM25, measure effectiveness |
| Index rebuild frequency | ❓ Open | On-demand for now, cache for performance |

---

## Notes

This plan builds on Plan #288 which provides the foundation (extraction script + hook). This plan:
1. Makes the manual mappings COMPLETE (not just what was there before)
2. Adds semantic search as a safety net for unmapped relationships
3. Adds validation to prevent mappings from becoming stale

The key insight from #288 exploration: "context exists ≠ context is used". This plan ensures context is both complete AND discoverable.
