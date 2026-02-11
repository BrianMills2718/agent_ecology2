# Current Context Graph System

How the documentation graph works today — routing context to AI assistants editing code.

**Last verified:** 2026-02-09

**See also:** META-ADR-0005 (Hierarchical Context Compression), Pattern #09 (Documentation Graph)

**Source:** `scripts/relationships.yaml`, hooks in `.claude/hooks/`

---

## Overview

The context graph is a knowledge graph stored in `scripts/relationships.yaml` (1280 lines). Nodes are files (source, docs, ADRs). Edges are typed relationships between them. When an AI assistant reads or edits a file, hooks traverse the graph to inject relevant context — governing ADRs, coupled documentation, glossary terms, domain concepts.

The graph serves one purpose: **route the right compression level to the right task**. Editing `executor.py` needs governing ADRs (rationale) and coupled docs (sync requirements), not the entire codebase. Planning a multi-file change needs domain model concepts (how systems relate), not individual function signatures.

See META-ADR-0005 for why documentation layers are hierarchical compressions of the codebase at different zoom levels.

## Graph Structure

### `relationships.yaml` Sections

| Section | Type | Count | Purpose |
|---------|------|-------|---------|
| `adrs` | dict | 21 entries | ADR definitions (number → title, file) |
| `governance` | list | 66 entries | ADR → source file mappings with context |
| `couplings` | list | 27 entries | Source file → documentation mappings |
| `conceptual_model` | dict | 6 entries | Ontology entity definitions |
| `glossary` | dict | 21 entries | Term definitions with source files |
| `document_hierarchy` | dict | 3 layers | Reading order (orientation, reference, implementation) |
| `target_current_links` | list | 7 entries | Target ↔ current architecture links |
| `file_context` | dict | 16 entries | Per-file PRD, domain model, ADR references |
| `directory_defaults` | dict | 4 entries | Fallback context for directories |
| `orphan_detection` | dict | | Scan config for orphan docs |
| `claude_md` | dict | | CLAUDE.md validation config |
| `file_context_exempt` | list | 3 entries | Files exempt from context injection |

### Edge Types

```
governance:     ADR ──governs──→ Source file    (with context string)
couplings:      Source file ──documented_by──→ Architecture doc
file_context:   Source file ──references──→ PRD, Domain Model, ADR
conceptual_model: Entity ──defined_by──→ Source files
glossary:       Term ──sourced_from──→ Source files
target_current_links: Target doc ──vision_for──→ Current doc
document_hierarchy: Layer ──reading_order──→ Docs
```

### Node Types

Nodes are files, not abstract concepts. The graph contains:

- **Source files** (`src/**/*.py`) — 66 governed, 16 with explicit file_context
- **ADRs** (`docs/adr/*.md`) — 21 registered
- **Architecture docs** (`docs/architecture/current/*.md`) — coupled via `couplings`
- **PRDs** (`docs/prd/*.md`) — referenced in `file_context`
- **Domain models** (`docs/domain_model/*.yaml`) — referenced in `file_context` and `conceptual_model`
- **Ontology** (`docs/ONTOLOGY.yaml`) — represented via `conceptual_model` section
- **Glossary** (`docs/GLOSSARY.md`) — represented via `glossary` section

## How Context Flows

### Trigger: AI Reads a Source File

```
1. Hook: inject-governance-context.sh (PostToolUse:Read)
2. Script: get_governance_context.py
3. Reads: governance → ADRs that govern this file
         couplings → docs coupled to this file
4. Output: System-reminder injected into AI context
```

The AI sees which ADRs constrain the file and which docs must stay in sync.

### Trigger: AI Edits a Source File

**Before edit:**
```
1. Hook: gate-edit.sh (PreToolUse:Edit/Write)
2. Script: check_required_reading.py
3. Reads: couplings → docs this file is coupled to
4. Behavior: BLOCKS edit if coupled docs haven't been read in this session
```

```
1. Hook: inject-edit-context.sh (PreToolUse:Edit)
2. Script: extract_relevant_context.py
3. Reads: glossary → matching terms for identifiers in the file
         conceptual_model → matching entities
         file_context → PRD capabilities, domain concepts, ADRs
         directory_defaults → fallback if no explicit file_context
4. Output: System-reminder with relevant glossary, ontology, domain context
```

**After edit:**
```
1. Hook: post-edit-quiz.sh (PostToolUse:Edit/Write)
2. Script: generate_quiz.py
3. Reads: governance → ADR constraints
         couplings → docs that need updating
4. Output: Understanding quiz (advisory, never blocks)
```

### Trigger: Git Commit (Pre-commit Hook)

```
1. Hook: pre-commit
2. Script: check_doc_coupling.py
3. Reads: couplings → strict couplings for changed files
4. Behavior: BLOCKS commit if strict-coupled doc was not updated alongside source
```

## Enforcement Levels

Each section of the graph has a different enforcement level:

| Section | Level | Mechanism | What Happens on Violation |
|---------|-------|-----------|---------------------------|
| `couplings` (strict) | **ENFORCED** | `check_doc_coupling.py` in pre-commit | Commit blocked |
| `couplings` (soft) | ADVISORY | Same script, warning only | Warning printed |
| `governance` | **CONSUMED** | `inject-governance-context.sh` | Context injected; no block |
| `governance` (sync) | **ENFORCED** | `sync_governance.py --check` in pre-commit | Commit blocked if headers stale |
| `file_context` | **CONSUMED** | `inject-edit-context.sh` | Context injected before edit |
| `glossary` | **CONSUMED** | `extract_relevant_context.py` | Terms injected before edit |
| `conceptual_model` | **CONSUMED** | `extract_relevant_context.py` | Entities injected before edit |
| `document_hierarchy` | DECLARED | Nothing reads it at runtime | Unused |
| `target_current_links` | **CONSUMED** | `get_governance_context.py` | Target/current vision injected |
| `orphan_detection` | DECLARED | No script consumes it | Unused |

**Key distinction:** ENFORCED = code blocks on violation (commit fails, edit blocked). CONSUMED = code reads and injects but doesn't block. DECLARED = exists in YAML but nothing reads it.

## Compression Hierarchy

The graph routes between documentation layers that compress the codebase at different zoom levels (META-ADR-0005):

```
Zoom 0:  Code              (~15,000 lines)  "What does this line do?"
Zoom 1:  Architecture docs  (~2,000 lines)  "How does this system work?"
Zoom 2:  Ontology           (~300 lines)    "What entities exist and what fields?"
Zoom 3:  Domain model       (~50 lines/domain) "How do concepts relate?"
Zoom 4:  Glossary           (~30 terms)     "What does this word mean?"
Zoom 5:  Thesis             (~1 paragraph)  "Why does this project exist?"
```

ADRs are orthogonal — they compress **rationale** (why decisions were made), not structure. This is information that doesn't exist anywhere in the code.

### Layer Freshness

| Layer | Freshness Mechanism | Status |
|-------|---------------------|--------|
| Architecture docs | CI-enforced doc-code coupling | Automated |
| ADR governance headers | `sync_governance.py --check` | Automated |
| Ontology | None | Manual review only |
| Domain model | None | Manual review only |
| Glossary | None (deprecated terms marked) | Manual review only |
| Thesis | Rarely changes | Stable |
| PRDs | None | Manual review only |

## Scripts

13 Python scripts consume `relationships.yaml`:

| Script | Purpose | Enforcement |
|--------|---------|-------------|
| `check_doc_coupling.py` | Verify docs updated with source | ENFORCE |
| `sync_governance.py` | Sync ADR headers in source files | ENFORCE |
| `check_required_reading.py` | Block edits if docs not read | ENFORCE |
| `check_governance_completeness.py` | Audit governance coverage | WARN |
| `check_claude_md.py` | Validate CLAUDE.md presence | WARN |
| `get_governance_context.py` | Return governance context for a file | CONSUME |
| `file_context.py` | Unified context loader | CONSUME |
| `extract_relevant_context.py` | Match glossary/ontology to source | CONSUME |
| `generate_quiz.py` | Post-edit understanding quiz | CONSUME |
| `build_doc_index.py` | Build searchable doc index | CONSUME |
| `generate_doc_graph_html.py` | D3.js graph visualization | CONSUME |
| `visualize_doc_graph.py` | Text/DOT graph visualization | CONSUME |
| `audit_governance_mappings.py` | Audit governance completeness | CONSUME |

## Configuration

Context routing is configured in `meta-process.yaml`:

```yaml
visibility:
  context_surfacing: both      # automatic | on-demand | both
  quiz_mode: both              # automatic | on-demand | both

enforcement:
  strict_doc_coupling: false   # When false, soft couplings are advisory
  show_strictness_warning: true

custom_docs:                   # Additional docs injected per path
  simulation_learnings:
    path: docs/SIMULATION_LEARNINGS.md
    surface_when: ["src/simulation/", "src/agents/", "config/genesis/agents/"]
```

## Validation

`validate_relationships.py` checks internal consistency of `relationships.yaml`:

```bash
python scripts/validate_relationships.py  # Full validation (run in pre-commit)
```

Checks: stale governance sources, unregistered ADR references, duplicate entries, broken coupling sources/docs, broken file_context entries, ADR file registration, governance coverage.

## Known Issues

1. **2 sections unused** — `document_hierarchy` and `orphan_detection` are declared but no script reads them (kept as informational data)
2. **No traceability chain** — Thesis→PRD→ADR→Plan→Code is conceptual but not encoded as graph edges
3. **Manual maintenance** — the YAML is entirely hand-maintained; no tooling generates it
