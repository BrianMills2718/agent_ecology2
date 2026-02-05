# Plan #294: Document Hierarchy and Context Injection Meta-Process

**Status:** Planning
**Priority:** High
**Theme:** Meta-Process
**Created:** 2026-02-05

---

## Problem Statement

Claude Code repeatedly fails to implement user vision faithfully because:
1. Vision specs (PRDs) don't exist
2. Domain models don't exist
3. When specs exist, they're not injected at the right moment
4. When specs don't exist, nobody flags the gap

The existing infrastructure (CLAUDE.md, ADRs, context injection, doc coupling) doesn't solve this because it operates at the wrong level - governance/glossary instead of vision/capabilities.

---

## Proposed Document Hierarchy

```
Thesis/Goals
    ↓
PRD (Product Requirements - capabilities)
    ↓
Domain Model (concepts that enable capabilities)
    ↓
ADR (architectural decisions for implementing concepts)
    ↓
Ontology/Schema (precise entity definitions)
    ↓
Plans (how to implement specific pieces)
    ↓
Code
```

### Layer Definitions

| Layer | Captures | Format | Location |
|-------|----------|--------|----------|
| Thesis | Why project exists, ultimate goals | Prose | `docs/THESIS.md` |
| PRD | What capabilities enable thesis | Structured | `docs/prd/{domain}.md` |
| Domain Model | What concepts enable capabilities | YAML + prose | `docs/domain_model/{domain}.yaml` |
| ADR | How to implement concepts | Structured | `docs/adr/` (existing) |
| Ontology | Precise entity definitions | YAML | `docs/ONTOLOGY.yaml` (rename from CONCEPTUAL_MODEL) |
| Plans | Specific implementation work | Structured | `docs/plans/` (existing) |
| Code | Implementation | Python | `src/` |

### Example: Agent Domain

| Layer | Content |
|-------|---------|
| Thesis | "Demonstrate emergent collective capability from LLM agents under resource constraints" |
| PRD | "Agents must be capable of: long-term goal pursuit, learning/adaptation, ecosystem awareness, niche differentiation, collaboration" |
| Domain Model | Concepts: Agent, Goal, TaskQueue, WorldModel, SelfModel, Niche, Ecosystem - with relationships |
| ADR | "ADR-00XX: BabyAGI-style task architecture for agent cognition" |
| Ontology | `artifact.goal_hierarchy: list[Goal]`, `artifact.world_model_id: str`, etc. |
| Plan | "Plan #295: Implement BabyAGI for discourse_analyst" |
| Code | `src/agents/discourse_analyst/...` |

---

## Per-File Context Linkage

Every source file has explicit links to its governing documents. This is the core mechanism.

### Storage: Extended relationships.yaml

```yaml
# scripts/relationships.yaml (extended)

# Existing: doc-to-doc coupling (preserved)
couplings:
  src/world/ledger.py: [docs/architecture/current/resources.md]

# Existing: ADR governance (preserved)
governance:
  docs/adr/0002_scrip.md: [src/world/ledger.py]

# NEW: Full context linkage per file
file_context:
  src/agents/agent.py:
    thesis: [emergence, scarcity-drives-behavior]
    prd: [agents#long-term-planning, agents#adaptation]
    domain_model: [agents#Goal, agents#WorldModel, agents#Niche]
    adr: [00XX_babyagi_architecture]
    ontology: [artifact#has_loop, artifact#has_standing]

  src/agents/workflow.py:
    prd: [agents#adaptation]
    domain_model: [agents#TaskQueue]
    adr: [00XX_babyagi_architecture]

  src/world/ledger.py:
    thesis: [scarcity-drives-behavior]
    prd: [resources#scarcity, resources#trading]
    domain_model: [resources#Scrip, resources#Budget]
    adr: [0002_scrip_nonnegative]
    ontology: [resources#depletable]

# NEW: Directory defaults (fallback if file not explicitly listed)
directory_defaults:
  src/agents/:
    prd: [agents]
    domain_model: [agents]
  src/world/:
    prd: [resources, contracts]
    domain_model: [resources, contracts]
```

### Resolution Order

When looking up context for a file:
1. **Exact file match** in `file_context` → use those links
2. **Directory default** in `directory_defaults` → use as fallback
3. **No match** → WARNING: file has no context links

### Link Format

Links use the format `doc_name#section_id`:
- `agents#long-term-planning` → `docs/prd/agents.md` section `#long-term-planning`
- `agents#Goal` → `docs/domain_model/agents.yaml` concept `Goal`
- `00XX_babyagi_architecture` → `docs/adr/00XX_babyagi_architecture.md`

---

## Context Injection Flow

### PreToolUse Hook (Edit operations)

```
┌─────────────────────────────────────────────────────────────────┐
│ Claude Code: Edit src/agents/agent.py                          │
│                      │                                          │
│                      ▼                                          │
│             ┌─────────────────┐                                │
│             │ Lookup file in  │                                │
│             │ relationships   │                                │
│             │ .yaml           │                                │
│             └────────┬────────┘                                │
│                      │                                          │
│        ┌─────────────┴─────────────┐                           │
│        ▼                           ▼                           │
│ ┌─────────────┐            ┌─────────────┐                    │
│ │ File found  │            │ File NOT    │                    │
│ │ with links  │            │ found       │                    │
│ └──────┬──────┘            └──────┬──────┘                    │
│        │                          │                            │
│        ▼                          ▼                            │
│ ┌─────────────┐            ┌─────────────┐                    │
│ │ Load linked │            │ WARNING:    │                    │
│ │ docs:       │            │ No context  │                    │
│ │ - Thesis    │            │ links for   │                    │
│ │ - PRD       │            │ this file.  │                    │
│ │ - DM        │            │ Add to      │                    │
│ │ - ADR       │            │ relation-   │                    │
│ │ - Ontology  │            │ ships.yaml  │                    │
│ └──────┬──────┘            └─────────────┘                    │
│        │                                                       │
│        ▼                                                       │
│ ┌─────────────────────────────────────────┐                   │
│ │ Inject as additionalContext:            │                   │
│ │                                          │                   │
│ │ ## Thesis                               │                   │
│ │ This file serves: emergence             │                   │
│ │                                          │                   │
│ │ ## Governing PRD: agents                │                   │
│ │ Capabilities this file implements:      │                   │
│ │ - long-term-planning: Agents pursue...  │                   │
│ │ - adaptation: Agents learn from...      │                   │
│ │                                          │                   │
│ │ ## Domain Model Concepts                │                   │
│ │ - Goal: Hierarchical objective...       │                   │
│ │ - WorldModel: Agent's understanding...  │                   │
│ │                                          │                   │
│ │ ## Relevant ADR                         │                   │
│ │ ADR-00XX: BabyAGI-style task arch...    │                   │
│ └─────────────────────────────────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

### What Gets Injected (by weight level)

| Weight | Injected Content |
|--------|------------------|
| light | Nothing (disabled) |
| medium | Warning if no links; capability/concept names only |
| heavy | Full PRD sections, domain model concepts, ADR summaries |
| strict | Same as heavy + block if links missing |

---

## File Lifecycle Enforcement

### 1. New File Created

```
PR adds: src/agents/goal_manager.py

CI check:
  ✗ src/agents/goal_manager.py has no entry in file_context
  ✗ No directory_default covers this path specifically enough

  Action required:
  Add to scripts/relationships.yaml:
    file_context:
      src/agents/goal_manager.py:
        prd: [agents#long-term-planning]
        domain_model: [agents#Goal]
```

### 2. Existing File Edited

```
Claude Code: Edit src/agents/agent.py

PreToolUse hook:
  → Lookup src/agents/agent.py in relationships.yaml
  → Found: prd=[agents#long-term-planning, agents#adaptation], ...
  → Load docs/prd/agents.md sections
  → Load docs/domain_model/agents.yaml concepts
  → Inject as additionalContext

Claude Code now sees governing specs before making changes.
```

### 3. Linked Doc Changes

```
PR modifies: docs/prd/agents.md#long-term-planning

CI check:
  Files linked to this section:
  - src/agents/agent.py
  - src/agents/workflow.py
  - src/agents/planning.py

  WARNING: These files may need review after PRD change.
  Add 'reviewed: [agents#long-term-planning]' to PR description
  OR update the files.
```

### 4. File Moved/Renamed

```
PR moves: src/agents/agent.py → src/agents/core/agent.py

CI check:
  ✗ src/agents/agent.py in file_context but file doesn't exist
  ✗ src/agents/core/agent.py has no entry in file_context

  Action required: Update relationships.yaml paths
```

---

## Document-to-Document Linking

Separate from file→doc linking, docs link to each other:

### Upward References (in frontmatter)

```yaml
# docs/prd/agents.md
---
id: prd/agents
thesis_refs: [emergence, scarcity-drives-behavior]
---

# docs/domain_model/agents.yaml
---
id: domain_model/agents
prd_refs: [agents#long-term-planning, agents#adaptation]
---

# docs/adr/00XX_babyagi_architecture.md
---
id: adr/00XX_babyagi
domain_model_refs: [agents#Goal, agents#TaskQueue]
---
```

### Downward References (auto-generated)

Script scans all docs and appends:

```yaml
# Auto-added to docs/prd/agents.md
implemented_by:
  domain_models: [domain_model/agents]
  files: [src/agents/agent.py, src/agents/workflow.py, ...]
```

---

## Open Uncertainties: Linkage & Injection

### Linkage Uncertainties

**U1: In-file vs centralized storage?**
- Option A: Links in `relationships.yaml` (centralized, one place to look)
- Option B: Links in file headers as comments (co-located, but scattered)
- Option C: Both (file headers authoritative, yaml auto-generated)
- **Current choice:** Option A (centralized) - but is this right?

**U2: Granularity of file_context entries?**
- Every file individually? (precise but verbose)
- Directory defaults only? (simple but imprecise)
- Hybrid? (defaults + overrides for specific files)
- **Current choice:** Hybrid - but where's the right balance?

**U3: How to handle files touching multiple domains?**
- `src/world/world.py` touches agents, resources, contracts, artifacts
- List all domains? Gets verbose.
- Primary domain + secondary?
- **Uncertain:** Need practical experience to decide

**U4: What about test files?**
- Should `tests/unit/test_agent.py` link to same docs as `src/agents/agent.py`?
- Auto-derive from source file being tested?
- Separate test-specific context?
- **Uncertain:** Not addressed yet

**U5: How to handle generated files?**
- `docs/plans/CLAUDE.md` is auto-generated
- Should it have context links?
- **Uncertain:** Probably exclude from system

### Injection Uncertainties

**U6: How much context is too much?**
- Full PRD + domain model + ADRs could be 10KB+
- Does this overflow context? Slow things down?
- **Uncertain:** May need summarization or selective loading

**U7: When to inject vs when to warn?**
- Inject on Read too, or only Edit?
- Inject on Glob/Grep?
- **Uncertain:** Edit seems clear; others less so

**U8: How to handle missing sections?**
- Link points to `agents#collaboration` but section doesn't exist
- Hard error? Warning? Skip?
- **Current choice:** Warning, but need validation script

**U9: Caching injected context?**
- If editing multiple files in same domain, re-fetch each time?
- Cache per-session? Per-domain?
- **Uncertain:** Performance optimization for later

### Process Uncertainties

**U10: Who maintains file_context mappings?**
- Claude Code when creating files?
- User when creating PRDs?
- CI enforcement? (files must have links)
- **Current choice:** CI enforcement, but who adds initially?

**U11: When do links get added?**
- When file is created?
- When PRD is created?
- Retroactively for existing codebase?
- **Uncertain:** Need bootstrap strategy for existing files

**U12: How to validate link freshness?**
- File last modified: 2026-02-01
- Linked PRD last modified: 2026-02-05
- Does file need review? How to know?
- **Uncertain:** Staleness detection is hard

**U13: How to handle refactoring?**
- Rename concept in domain model
- All file links using old concept name break
- **Uncertain:** Need migration strategy or stable IDs

---

## Open Questions / Uncertainties

### Hierarchy Questions

1. **Is the hierarchy strictly linear or a graph?**
   - Can an ADR reference multiple PRDs?
   - Can a plan implement multiple ADRs?
   - Instinct: It's a DAG, not a strict tree

2. **How granular are PRDs?**
   - One PRD per domain (agents, resources, contracts)?
   - One PRD per capability (planning, collaboration)?
   - One master PRD with sections?

3. **Where does the thesis come from?**
   - It partially exists in CLAUDE.md
   - Should it be extracted to its own file?
   - Or is CLAUDE.md the thesis?

### Domain Model Questions

4. **What's the relationship between Domain Model and Ontology?**
   - Domain Model: conceptual, human-readable ("Agent pursues Goals")
   - Ontology: precise, machine-readable ("artifact.goal_hierarchy: list")
   - How do we keep them in sync?

5. **How detailed should domain models be?**
   - Just concepts and relationships?
   - Also behaviors and constraints?
   - Examples and non-examples?

### Linking Questions

6. **How do we handle cross-cutting concerns?**
   - "Observability" touches all domains
   - Does it get its own PRD? Or sections in each domain PRD?

7. **How do we prevent link rot?**
   - Docs get renamed/moved
   - Need validation that links resolve

### Injection Questions

8. **How do we detect domain from file path?**
   - Simple mapping: `src/agents/** → agents domain`
   - What about files that touch multiple domains?

9. **How much context is too much?**
   - Injecting full PRD + domain model + ADRs could be huge
   - Need summarization or selective injection?

10. **Who maintains the mappings?**
    - Manual: file → domain mapping in config
    - Auto: infer from file content/imports

### Process Questions

11. **Who creates PRDs and domain models?**
    - User provides vision, Claude Code drafts docs?
    - User writes them directly?
    - Collaborative iteration?

12. **When do these docs get created?**
    - Before any implementation in a domain?
    - Retroactively for existing domains?
    - Incrementally as needed?

13. **How do we avoid bureaucratic overhead?**
    - Every small change needs PRD update?
    - Or PRDs are stable, plans handle details?

---

## Proposed Next Steps

### Phase 1: Foundation (do now?)
1. Extract/create `docs/THESIS.md` from CLAUDE.md philosophy section
2. Create `docs/prd/` directory structure
3. Create `docs/domain_model/` directory structure
4. Rename CONCEPTUAL_MODEL.yaml → ONTOLOGY.yaml

### Phase 2: Test Case - Agents
1. Write `docs/prd/agents.md` - agent capabilities
2. Write `docs/domain_model/agents.yaml` - agent concepts
3. Create ADR for agent cognitive architecture (BabyAGI-style)
4. Update ONTOLOGY.yaml with agent-specific fields
5. See if this would have prevented the discourse_analyst confusion

### Phase 3: Injection Mechanism
1. Create domain → docs mapping
2. Implement PreToolUse hook for context injection
3. Implement missing-spec detection
4. Test on real implementation work

### Phase 4: Enforcement
1. Add to CI: plans must reference PRDs
2. Add to CI: PRDs must exist for touched domains
3. Add link validation (no broken references)

---

## Success Criteria

1. When Claude Code works on agents, agent PRD and domain model are automatically injected
2. If agent PRD doesn't exist, Claude Code is warned before implementation
3. Every plan traces back to a PRD traces back to thesis
4. User's vision for "sophisticated agents" is captured in PRD/domain model
5. Implementation matches vision because vision is visible during implementation

---

## Concrete Interlinking Mechanics

### Machine-Readable Reference Format

Every document has a YAML frontmatter with explicit references:

```yaml
---
# In docs/prd/agents.md
id: prd/agents
type: prd
domain: agents
thesis_refs:
  - docs/THESIS.md#emergence
  - docs/THESIS.md#scarcity-drives-behavior
capabilities:
  - id: long-term-planning
    description: "Agents pursue goals across multiple interactions"
  - id: adaptation
    description: "Agents learn from environment and modify behavior"
  - id: niche-finding
    description: "Agents discover unique value propositions"
---
```

```yaml
---
# In docs/domain_model/agents.yaml
id: domain_model/agents
type: domain_model
domain: agents
prd_refs:
  - docs/prd/agents.md#long-term-planning
  - docs/prd/agents.md#adaptation
concepts:
  - id: Goal
    enables: [long-term-planning]
  - id: WorldModel
    enables: [adaptation, niche-finding]
---
```

### Reference Validation Script

```bash
# Check all references resolve
python scripts/check_doc_refs.py --validate

# Output:
# ✓ docs/prd/agents.md → docs/THESIS.md#emergence (valid)
# ✗ docs/domain_model/agents.yaml → docs/prd/agents.md#collaboration (NOT FOUND)
```

### Auto-Generated Downward Links

Script scans all docs and generates "implemented by" sections:

```yaml
# Auto-appended to docs/prd/agents.md
implemented_by:
  domain_models:
    - docs/domain_model/agents.yaml
  adrs:
    - docs/adr/00XX_babyagi_architecture.md
  plans:
    - docs/plans/295_discourse_analyst_babyagi.md
```

---

## Update Enforcement Rules

### Change Propagation Matrix

| When this changes... | Check/update these... | Enforcement |
|---------------------|----------------------|-------------|
| Thesis | All PRDs still align | Manual review |
| PRD capability | Domain models that reference it | CI warning |
| Domain model concept | ADRs that implement it | CI warning |
| ADR | Plans that reference it | CI warning |
| Ontology field | Code that uses it | CI error (existing) |
| Plan | Code in PR | CI check (existing) |

### Staleness Detection

```bash
# Detect docs that reference changed parents
python scripts/check_doc_staleness.py

# Output:
# WARNING: docs/domain_model/agents.yaml references docs/prd/agents.md
#          PRD was modified 2026-02-01, domain model last updated 2026-01-15
#          Review needed: domain model may be stale
```

### Update Workflow

When changing a document:
1. CI checks what references this document (downward)
2. CI checks what this document references (upward)
3. Flags potential staleness in either direction
4. Requires explicit "reviewed: no changes needed" or actual updates

---

## Context Injection Flow

### Trigger → Domain → Documents

```yaml
# config/domain_mappings.yaml
domains:
  agents:
    file_patterns:
      - "src/agents/**"
      - "src/world/agent_*.py"
    required_docs:
      - docs/prd/agents.md
      - docs/domain_model/agents.yaml
    optional_docs:
      - docs/adr/00XX_babyagi_architecture.md

  resources:
    file_patterns:
      - "src/world/ledger.py"
      - "src/world/resource_*.py"
    required_docs:
      - docs/prd/resources.md
      - docs/domain_model/resources.yaml
```

### Injection Hook Logic

```bash
# .claude/hooks/inject-domain-context.sh (PreToolUse for Edit)

1. Extract file path from tool input
2. Match against domain_mappings.yaml patterns
3. For each matching domain:
   a. Check required_docs exist
   b. If missing: inject WARNING
   c. If present: inject doc content (or summary)
4. Return additionalContext
```

### What Gets Injected

**Full injection (heavy mode):**
- Complete PRD for domain
- Complete domain model
- Relevant ADR summaries
- Ontology section for domain

**Summary injection (medium mode):**
- PRD capability list (not full prose)
- Domain model concept list with one-line descriptions
- ADR titles and status

**Minimal injection (light mode):**
- Just warnings for missing specs
- Links to docs (not content)

---

## Weight-Based Configurability

Extends existing meta-process weight system (Plan #218):

```yaml
# config/meta_process.yaml
weight: heavy  # light | medium | heavy | strict

doc_hierarchy:
  light:
    require_thesis: false
    require_prd: false
    require_domain_model: false
    inject_context: false
    warn_missing_specs: false

  medium:
    require_thesis: true
    require_prd: false  # Optional
    require_domain_model: false
    inject_context: true
    inject_mode: summary
    warn_missing_specs: true

  heavy:
    require_thesis: true
    require_prd: true
    require_domain_model: true
    inject_context: true
    inject_mode: full
    warn_missing_specs: true
    block_on_missing: false  # Warn but allow

  strict:
    require_thesis: true
    require_prd: true
    require_domain_model: true
    inject_context: true
    inject_mode: full
    warn_missing_specs: true
    block_on_missing: true  # Cannot proceed without specs
```

### Transitioning Weights

Projects can start light and increase:
1. **Light**: Just code, minimal process
2. **Medium**: Add thesis, warn on missing specs
3. **Heavy**: Require PRDs and domain models, full injection
4. **Strict**: Block implementation without specs

---

## References

- Current: `docs/CONCEPTUAL_MODEL.yaml` (to become ONTOLOGY.yaml)
- Current: `docs/adr/` (ADR system)
- Current: `.claude/hooks/inject-governance-context.sh` (context injection)
- Current: `scripts/relationships.yaml` (doc coupling)
- Current: `config/meta_process.yaml` (weight system)
- Discussion: Session conversation about agent architecture and meta-process gaps
