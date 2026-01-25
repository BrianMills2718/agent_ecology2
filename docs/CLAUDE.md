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
├── archive/              # Historical/deprecated docs
├── plans/                # Gap tracking + implementation plans
├── GLOSSARY.md           # Canonical terminology (single source)
├── DESIGN_CLARIFICATIONS.md  # Decision rationale archive
└── SECURITY.md           # Security model

# See also:
meta/
├── patterns/             # Reusable meta-process patterns (moved from docs/meta/)
└── acceptance_gates/     # Feature specifications (moved from root)
```

## Key Files

| File | Purpose | When to Update |
|------|---------|----------------|
| `adr/` | Architecture Decision Records | New architectural decisions |
| `../meta/patterns/` | Reusable process patterns | New patterns identified |
| `../meta/acceptance_gates/` | Feature specifications | New features defined |
| `GLOSSARY.md` | Canonical terminology | New concepts added |
| `DESIGN_CLARIFICATIONS.md` | WHY decisions were made | Architecture discussions |
| `SECURITY.md` | Security model and boundaries | Security changes |

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

## CI Enforcement

**Unified documentation graph:** `scripts/relationships.yaml`
```bash
python scripts/check_doc_coupling.py --suggest  # Doc-code coupling
python scripts/sync_governance.py --check       # ADR governance
python scripts/validate_plan.py --plan N        # Pre-implementation validation
```
