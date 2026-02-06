# Documentation Directory

All extended documentation lives here. Root CLAUDE.md has the overview.

## Structure

```
docs/
├── THESIS.md             # Why this project exists (read first)
├── prd/                  # Product requirements by domain (capabilities)
├── domain_model/         # Conceptual models by domain (concepts)
├── adr/                  # Architecture Decision Records (immutable)
├── architecture/
│   ├── current/          # What IS implemented (source of truth)
│   ├── target/           # What we WANT (aspirational)
│   └── gaps/             # Comprehensive gap analysis (142 gaps)
├── plans/                # Active implementation plans only
├── ONTOLOGY.yaml         # Precise entity definitions (machine-readable)
├── catalog.yaml          # Agent lineage tracking (moved from src/agents/, Plan #299)
├── GETTING_STARTED.md    # Installation, config, development
├── GLOSSARY.md           # Canonical terminology (single source)
├── UNCERTAINTIES.md      # Open questions needing human review (Plan #306)
├── DESIGN_CLARIFICATIONS.md  # Decision rationale archive
├── SECURITY.md           # Security model
└── drafts/               # Work-in-progress captured thoughts

# See also:
meta/
├── patterns/             # Reusable meta-process patterns
└── acceptance_gates/     # Feature specifications

# External archive (not in repo):
/home/brian/brian_projects/archive/agent_ecology2/docs/
├── plans/                # Completed plans (1-239)
├── research/             # Historical research notes
└── (historical docs)     # Old design discussions, handbooks, etc.
```

## Key Files

| File | Purpose | When to Update |
|------|---------|----------------|
| `THESIS.md` | Why this project exists, core proposition | Rarely (foundational) |
| `prd/` | Capability requirements by domain | New capabilities identified |
| `domain_model/` | Conceptual models by domain | New concepts for capabilities |
| `adr/` | Architecture Decision Records | New architectural decisions |
| `../meta/patterns/` | Reusable process patterns | New patterns identified |
| `../meta/acceptance_gates/` | Feature specifications | New features defined |
| `ONTOLOGY.yaml` | Precise entity definitions (was CONCEPTUAL_MODEL) | Field-level changes |
| `GETTING_STARTED.md` | Installation, configuration, development | Setup/tooling changes |
| `GLOSSARY.md` | Canonical terminology | New concepts added |
| `CONCERNS.md` | Open concerns and known issues | New concerns identified |
| `UNCERTAINTIES.md` | Open questions needing human review | New ambiguities found |
| `DEFERRED_FEATURES.md` | Features intentionally deferred | Deferral decisions |
| `DESIGN_CLARIFICATIONS.md` | WHY decisions were made | Architecture discussions |
| `DOCKER.md` | Docker setup and containerization | Docker config changes |
| `SCHEMA_AUDIT.md` | Config schema audit findings | Schema changes |
| `SECURITY.md` | Security model and boundaries | Security changes |
| `THREAT_MODEL.md` | Threat analysis and mitigations | Security model changes |
| `V1_ACCEPTANCE.md` | V1 acceptance criteria and readiness | Milestone progress |
| `references` | Symlink to shared references (external) | External references |
| `drafts/` | Work-in-progress captured thoughts | Ongoing exploration |
| `SIMULATION_LEARNINGS.md` | Observations from running simulations | After simulation experiments |
| `EXPLORATION_NOTES_288.md` | Exploration notes for Plan #288 (context provision) | Historical |

## Doc Types

| Type | Location | Updates |
|------|----------|---------|
| Current reality | `architecture/current/` | After code changes |
| Future vision | `architecture/target/` | Architecture decisions |
| ADRs | `adr/` | New architectural decisions (immutable once accepted) |
| Process patterns | `../meta/patterns/` | Reusable patterns identified |
| Feature specs | `../meta/acceptance_gates/` | Feature definitions |
| Implementation | `plans/` | Gap identified/closed |
| Decisions | `DESIGN_CLARIFICATIONS.md` | When debating approaches |

## Simulation Learnings

Document observations from running simulations in `SIMULATION_LEARNINGS.md`.

**Principles:**
- Use weak models (gemini-2.0-flash) to stress-test architecture
- If weak models can't bootstrap, we're relying on model intelligence to paper over weaknesses
- Avoid prescriptive fixes that don't scale (hard-coding every failure case)
- Focus on conditions for emergence: metacognition, self-modification, evolutionary pressure

**After running simulations, record:**
- Model comparison results (quantitative)
- Behavioral observations (qualitative)
- Wrong lessons avoided (prescriptive traps)
- Right lessons learned (architectural insights)
- Future experiment ideas

## Document Hierarchy (Plan #294)

Documentation follows a layered structure from vision to code:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 0: THESIS (Why we exist)                                      │
│   docs/THESIS.md                      → Core proposition            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: CAPABILITIES (What we need)                                │
│   docs/prd/{domain}.md                → Capabilities by domain      │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 2: CONCEPTS (How we think about it)                           │
│   docs/domain_model/{domain}.yaml     → Concepts enabling caps      │
│   docs/GLOSSARY.md                    → Terminology definitions     │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 3: ARCHITECTURE (How we build it)                             │
│   docs/adr/                           → Architectural decisions     │
│   docs/architecture/target/           → Where we're heading         │
│   docs/ONTOLOGY.yaml                  → Precise entity definitions  │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 4: IMPLEMENTATION (What exists now)                           │
│   docs/architecture/current/*.md      → How each system works       │
│   docs/plans/                         → Active implementation work  │
│   (Coupled to source code - CI enforced)                            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 5: CODE (Source of truth)                                     │
│   src/**/*.py                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Linking:** Each layer references its parent. See `scripts/relationships.yaml` for file-level mappings.

## CI Enforcement

**Unified documentation graph:** `scripts/relationships.yaml`
```bash
python scripts/check_doc_coupling.py --suggest  # Doc-code coupling
python scripts/sync_governance.py --check       # ADR governance
python scripts/validate_plan.py --plan N        # Pre-implementation validation
```
