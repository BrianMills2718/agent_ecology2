# Context Graph Gaps

Gaps between [current](../current/context_graph.md) and [target](../target/context_graph.md) context graph architecture.

**Last updated:** 2026-02-09

**Methodology:** Audit of `scripts/relationships.yaml`, all 13 consumer scripts, 4 hooks.

---

## Summary

| Metric | Value |
|--------|-------|
| Total gaps | 16 |
| Severity: High | 4 |
| Severity: Medium | 7 |
| Severity: Low | 5 |
| Estimated effort | 3-4 plans |

The context graph exists and works for its core use cases (governance injection, doc-code coupling). The main gaps are: stale data, unused sections, missing freshness enforcement for compression layers, and no traceability chain.

---

## Gap: Data Quality

### GAP-CTX-01: Stale governance entries (HIGH)

21 governance entries reference files that have been renamed or deleted. These produce silent failures — hooks can't find the file, so governance context is never injected.

**Fix:** Remove stale entries, add CI check that all `governance[].source` files exist.

### GAP-CTX-02: Unregistered ADRs (HIGH)

7 ADRs are referenced in governance edges but missing from the `adrs` section (including ADR-0027, ADR-0028). Scripts that try to look up ADR metadata for these get empty results.

**Fix:** Add missing ADR entries. Consider CI check that all ADR numbers in `governance[].adrs` exist in `adrs` section.

### GAP-CTX-03: Ungoverned source files (MEDIUM)

3 functional source files have no governance entry. They receive no ADR context when read or edited.

**Fix:** Add governance entries. Consider coverage enforcement (all `src/**/*.py` must have at least one governance entry).

### GAP-CTX-04: No graph self-validation (HIGH)

No script validates `relationships.yaml` holistically — checking that all referenced files exist, all ADR numbers resolve, coupling source patterns match real files, etc. Staleness accumulates silently.

**Fix:** Write `validate_relationships.py` that checks internal consistency. Run in pre-commit.

---

## Gap: Unused Sections

### GAP-CTX-05: document_hierarchy declared but unused (LOW)

The `document_hierarchy` section defines reading order layers (orientation, reference, implementation) but no script reads it. It's dead data.

**Fix:** Either write a consumer (inject reading suggestions for new contributors) or remove the section.

### GAP-CTX-06: target_current_links declared but unused (MEDIUM)

The `target_current_links` section maps target architecture docs to current architecture docs but no script reads it. When editing `current/contracts.md`, the AI doesn't see that `target/05_contracts.md` describes the vision.

**Fix:** Write a consumer that injects target doc references when editing current architecture docs. Low effort, high value.

### GAP-CTX-07: orphan_detection declared but unused (LOW)

The `orphan_detection` section configures orphan doc scanning but no script implements it.

**Fix:** Either implement orphan detection or remove the section. Orphan docs are a real problem (disconnected files accumulate), but the section is aspirational.

---

## Gap: Missing Freshness Enforcement

### GAP-CTX-08: Ontology has no freshness check (MEDIUM)

The ontology (`conceptual_model` section + `docs/ONTOLOGY.yaml`) describes entity fields but nothing checks whether these match actual dataclass fields in source. If someone adds a field to `Artifact`, the ontology doesn't know.

**Fix:** Script that compares ontology `key_fields` against actual dataclass/Pydantic model fields via AST inspection. Warn on drift.

### GAP-CTX-09: Domain model has no freshness check (MEDIUM)

Domain models (`docs/domain_model/*.yaml`) describe concept relationships but nothing validates them against source. If a module adds a new concept, the domain model doesn't know.

**Fix:** Script that checks domain model concept names appear in source module docstrings or class names. Heuristic, not exact.

### GAP-CTX-10: Glossary has no new-term detection (LOW)

The glossary has deprecated-term detection (via `extract_relevant_context.py`) but no mechanism to detect new terms in source that should be added to the glossary.

**Fix:** Script that extracts camelCase/PascalCase identifiers from changed files and checks against glossary. Report unrecognized domain terms.

### GAP-CTX-11: PRD freshness unknown (LOW)

PRDs describe capabilities but nothing checks whether capabilities described match implemented behavior. PRD content overlaps with ADR context sections.

**Fix:** Evaluate whether PRDs provide unique compression. If not, collapse into ADRs (per META-ADR-0005 evaluation).

---

## Gap: Missing Traceability

### GAP-CTX-12: No Thesis→PRD edges (MEDIUM)

The thesis describes the project purpose. PRDs describe required capabilities. There's no formal link between them. The thesis is an orphan node in the graph.

**Fix:** Add `thesis_links` section mapping thesis paragraphs to PRD domains.

### GAP-CTX-13: No PRD→ADR edges (MEDIUM)

PRDs describe what capabilities are needed. ADRs describe how we decided to build them. No formal link exists.

**Fix:** Add `prd_to_adr` section or extend `file_context` to include PRD→ADR references.

### GAP-CTX-14: No ADR→Plan edges (MEDIUM)

ADRs describe decisions. Plans implement them. The connection exists conceptually (plan files reference ADRs in headers) but isn't encoded in the graph for traversal.

**Fix:** Parse plan file headers for ADR references, auto-generate edges.

### GAP-CTX-15: No Plan→Source edges (LOW)

Plans list files they change. This information exists in plan files but isn't in the graph.

**Fix:** Parse plan file "Files Affected" sections, auto-generate edges. Nice for traceability visualization but low operational value (plans are ephemeral).

---

## Gap: Maintenance Burden

### GAP-CTX-16: Graph is entirely hand-maintained (HIGH)

The 1280-line `relationships.yaml` requires manual updates for every new file, every renamed file, every new ADR. This doesn't scale and is the root cause of GAP-CTX-01 through GAP-CTX-03.

**Fix:** Source-declared edges (files declare their own relationships) with a generator script that compiles them into `relationships.yaml`. See target architecture doc for design options.

---

## Prioritized Implementation Order

### Phase 1: Data Quality (1 plan)
- GAP-CTX-01: Clean stale governance entries
- GAP-CTX-02: Register missing ADRs
- GAP-CTX-03: Add missing governance entries
- GAP-CTX-04: Write `validate_relationships.py`

### Phase 2: Activate Dead Sections (1 plan)
- GAP-CTX-06: Consume target_current_links
- GAP-CTX-05: Decide on document_hierarchy (consume or remove)
- GAP-CTX-07: Decide on orphan_detection (implement or remove)

### Phase 3: Freshness Enforcement (1 plan)
- GAP-CTX-08: Ontology freshness check
- GAP-CTX-09: Domain model freshness check
- GAP-CTX-10: Glossary new-term detection
- GAP-CTX-11: PRD evaluation

### Phase 4: Traceability + Automation (1 plan, deferred)
- GAP-CTX-12 through GAP-CTX-15: Add traceability edges
- GAP-CTX-16: Source-declared edges (largest effort, most impact)

Phases 1-2 are small and immediately valuable. Phase 3 requires design decisions. Phase 4 is the strategic target but not urgent.
