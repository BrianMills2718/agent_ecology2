# Documentation Directory

All extended documentation lives here. Root CLAUDE.md has the overview.

## Structure

```
docs/
├── adr/                  # Architecture Decision Records (immutable)
├── architecture/
│   ├── current/          # What IS implemented (source of truth)
│   ├── target/           # What we WANT (aspirational)
│   └── gaps/             # Comprehensive gap analysis (142 gaps)
├── plans/                # Active implementation plans only
├── GETTING_STARTED.md    # Installation, config, development
├── GLOSSARY.md           # Canonical terminology (single source)
├── DESIGN_CLARIFICATIONS.md  # Decision rationale archive
└── SECURITY.md           # Security model

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
| `adr/` | Architecture Decision Records | New architectural decisions |
| `../meta/patterns/` | Reusable process patterns | New patterns identified |
| `../meta/acceptance_gates/` | Feature specifications | New features defined |
| `GETTING_STARTED.md` | Installation, configuration, development | Setup/tooling changes |
| `GLOSSARY.md` | Canonical terminology | New concepts added |
| `CONCEPTUAL_MODEL.yaml` | Structured conceptual model of the system | Model changes |
| `CONCERNS.md` | Open concerns and known issues | New concerns identified |
| `DEFERRED_FEATURES.md` | Features intentionally deferred | Deferral decisions |
| `DESIGN_CLARIFICATIONS.md` | WHY decisions were made | Architecture discussions |
| `DOCKER.md` | Docker setup and containerization | Docker config changes |
| `SCHEMA_AUDIT.md` | Config schema audit findings | Schema changes |
| `SECURITY.md` | Security model and boundaries | Security changes |
| `THREAT_MODEL.md` | Threat analysis and mitigations | Security model changes |
| `V1_ACCEPTANCE.md` | V1 acceptance criteria and readiness | Milestone progress |
| `references` | Symlink to shared references (external) | External references |

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

## Document Hierarchy (ADR-0005)

Documentation follows a layered structure. When joining the project or investigating issues, read from top to bottom:

```
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 1: ORIENTATION (Read first)                                   │
│   CLAUDE.md (root)                    → Process and workflow        │
│   docs/architecture/current/CORE_SYSTEMS.md → What subsystems exist │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 2: REFERENCE (Look up when needed)                            │
│   docs/CONCEPTUAL_MODEL.yaml          → Exact entities and fields   │
│   docs/GLOSSARY.md                    → Terminology definitions     │
│   docs/architecture/target/           → Where we're heading         │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 3: IMPLEMENTATION (Detailed current state)                    │
│   docs/architecture/current/*.md      → How each system works       │
│   (Coupled to source code - CI enforced)                            │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│ Layer 4: CODE (Source of truth)                                     │
│   src/**/*.py                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

**Target ↔ Current linking:** Each `target/` doc maps to a `current/` counterpart. See `scripts/relationships.yaml` for the full mapping.

## CI Enforcement

**Unified documentation graph:** `scripts/relationships.yaml`
```bash
python scripts/check_doc_coupling.py --suggest  # Doc-code coupling
python scripts/sync_governance.py --check       # ADR governance
python scripts/validate_plan.py --plan N        # Pre-implementation validation
```
