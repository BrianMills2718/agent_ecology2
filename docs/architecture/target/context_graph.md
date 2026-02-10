# Target Context Graph Architecture

Where the context graph system should evolve. Design goals and open questions.

**Last verified:** 2026-02-09

**See also:** META-ADR-0005 (Hierarchical Context Compression), Pattern #09 (Documentation Graph)

**See current:** [../current/context_graph.md](../current/context_graph.md)

---

## Design Goals

1. **Every file interlinked** — every source file, doc file, config file should have edges to every relevant file, not just the ones someone remembered to add
2. **Compression at every zoom** — AI assistants should be able to get the right level of detail for their task (single function → system → architecture → project purpose) without reading irrelevant material
3. **Freshness enforced, not hoped for** — every compression layer should have a staleness detection mechanism, not just the ones that happen to have CI checks
4. **Full traceability** — Thesis → PRD → ADR → Plan → Code should be a traversable chain, not a conceptual idea
5. **Low maintenance burden** — the graph should be mostly generated from source, not hand-maintained as a 1280-line YAML

## Target Edge Types

### Currently Working (Keep)

| Edge | Example | Enforcement |
|------|---------|-------------|
| Governance | ADR-0019 governs `permission_checker.py` | ENFORCED (sync + injection) |
| Doc-code coupling | `runner.py` coupled to `execution_model.md` | ENFORCED (pre-commit) |
| File context | `artifacts.py` → PRD capabilities, domain concepts | CONSUMED (edit injection) |

### Currently Declared Only (Activate)

| Edge | Example | Target Enforcement |
|------|---------|-------------------|
| Document hierarchy | Orientation → Reference → Implementation reading order | CONSUMED — inject reading suggestions for new contributors |
| Target-current links | `target/05_contracts.md` vision for `current/contracts.md` | CONSUMED — inject target vision when editing current docs |

### Currently Missing (Add)

| Edge | Example | Target Enforcement |
|------|---------|-------------------|
| Thesis → PRD | Thesis drives `prd/artifacts.md` capability requirements | DECLARED (traceability) |
| PRD → ADR | `prd/artifacts.md` requires ADR-0001 decisions | CONSUMED — inject PRD context when writing ADRs |
| ADR → Plan | ADR-0019 implemented by Plan #310 | CONSUMED — show implementation status |
| Plan → Source | Plan #311 changes `artifacts.py`, `kernel_contracts.py` | CONSUMED — already partially exists in plan files |
| Domain model → Ontology | Domain concept "artifact" specifies ontology entity | DECLARED (traceability) |
| Source → Source | `executor.py` calls `permission_checker.py` | CONSUMED — inject call-graph neighbors |

### Traceability Chain

The full chain from purpose to implementation:

```
Thesis  ──drives──→  PRD  ──requires──→  ADR  ──implemented_by──→  Plan  ──changes──→  Code
                                                                                         ↑
                                Architecture Doc  ──documents──→  Code  (doc-code coupling)
                                Domain Model  ──specifies──→  Ontology  ──maps_to──→  Code
                                Glossary  ──defines_terms_in──→  Code
```

Every node in this graph should be reachable from Thesis. Orphans indicate either missing edges or truly disconnected content (which should be deleted).

## Compression Layer Targets

Each layer should meet the three META-ADR-0005 criteria: uniquely useful, consumed, fresh.

| Layer | Current | Target |
|-------|---------|--------|
| **Architecture docs** | ENFORCED freshness via doc-code coupling | Keep as-is |
| **ADRs** | ENFORCED governance sync | Keep as-is |
| **Ontology** | CONSUMED (injected before edit) but NO freshness check | Add freshness: script that compares ontology entities against actual dataclass fields |
| **Domain model** | CONSUMED (file_context edges) but NO freshness check | Add freshness: script that checks domain model concept list against actual module exports |
| **Glossary** | CONSUMED (injected before edit) but NO freshness check | Add freshness: deprecated-term detection already exists; add new-term detection (source identifiers not in glossary) |
| **PRDs** | CONSUMED (file_context edges) but NO freshness check | Evaluate for collapse into ADRs (per META-ADR-0005). PRD content overlaps with ADR context sections |
| **Thesis** | Not consumed by any script | Stable; consider injecting for new-contributor onboarding context |

## Graph Maintenance

### Current Problem

The 1280-line `relationships.yaml` is entirely hand-maintained. Adding a new source file requires manually adding governance entries, coupling entries, and file_context entries. This doesn't scale.

### Target: Semi-automated Graph

1. **Source-declared edges**: Source files declare their relationships via structured comments or a companion `.context.yaml`:
   ```python
   # context: adr=[0001, 0019], prd=[artifacts#persistent-storage], domain=[artifacts#Artifact]
   ```
   Or companion file:
   ```yaml
   # src/world/artifacts.context.yaml
   adr: [0001, 0007, 0011, 0016]
   prd: [artifacts#persistent-storage, artifacts#universal-addressability]
   domain_model: [artifacts#Artifact, artifacts#ArtifactStore]
   ```

2. **Generated graph**: A script reads all source-declared edges and generates `relationships.yaml`. Hand-maintained sections (governance context strings, coupling descriptions) remain manual but are additive, not required.

3. **Coverage enforcement**: CI checks that every source file has at minimum: one ADR governance edge, one doc-code coupling. New files without edges fail CI until addressed.

### Open Questions

1. **Inline comments vs companion files?** Comments are easier to maintain (live with the code) but add noise. Companion files are cleaner but can drift from the files they describe. Leaning toward companion files since they can be validated.

2. **Should PRDs be collapsed into ADRs?** PRDs describe capabilities; ADRs describe decisions about how to implement them. There's significant overlap. But PRDs answer "what do we need?" while ADRs answer "how did we decide to build it?" — potentially distinct compression axes. Need more experience before deciding.

3. **Should the ontology be auto-generated from code?** The ontology currently mirrors dataclass fields from source. A script could generate it from AST inspection. But the ontology also includes hand-written descriptions and conceptual groupings that don't exist in code. Hybrid approach: auto-generate fields, hand-maintain descriptions.

4. **How much freshness enforcement is practical?** Every freshness check adds CI time and maintenance burden. The current system has 2 enforced checks (doc-coupling, governance sync) taking ~3 seconds total. Adding 3 more (ontology, domain model, glossary) is feasible but may create false positives that erode trust.

5. **Should source→source edges exist?** Import graphs are easily generated but very noisy. A curated "these files are architecturally related" graph is more useful but requires maintenance. The audit found that `file_context` already implicitly groups files via shared PRD/domain references — this may be sufficient.

## Migration Path

This is not a rewrite. Evolution from current:

1. **Clean up** — remove 21 stale governance entries, register 7 missing ADRs (small, immediate)
2. **Activate declared-only sections** — write consumers for `document_hierarchy` and `target_current_links` (medium)
3. **Add traceability edges** — encode Thesis→PRD, PRD→ADR, ADR→Plan links (medium)
4. **Add freshness checks** — ontology vs code, glossary vs code (medium, needs design)
5. **Evaluate PRD collapse** — try removing PRDs and see if any unique compression is lost (requires experience)
6. **Source-declared edges** — the big shift; requires new tooling and migration (large, deferred)
