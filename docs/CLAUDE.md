# Documentation Directory

All extended documentation lives here. Root CLAUDE.md has the overview.

## Structure

```
docs/
├── architecture/
│   ├── current/    # What IS implemented (source of truth)
│   ├── target/     # What we WANT (aspirational)
│   └── gaps/       # Gap tracking system (single source of truth)
├── features/       # Feature-specific documentation
├── plans_archived/ # ARCHIVED - merged into architecture/gaps/
├── GLOSSARY.md     # Canonical terminology
├── DESIGN_CLARIFICATIONS.md  # Decision rationale archive
└── SECURITY.md     # Security model
```

## Key Files

| File | Purpose | When to Update |
|------|---------|----------------|
| `architecture/gaps/CLAUDE.md` | **Gap tracking (142 gaps, 31 epics)** | Gap status changes |
| `GLOSSARY.md` | Canonical terms (scrip, principal, tick) | New concepts added |
| `DESIGN_CLARIFICATIONS.md` | WHY decisions were made | Architecture discussions |
| `SECURITY.md` | Security model and boundaries | Security changes |

## Doc Types

| Type | Location | Updates |
|------|----------|---------|
| Current reality | `architecture/current/` | After code changes |
| Future vision | `architecture/target/` | Architecture decisions |
| Gap tracking | `architecture/gaps/` | Gap identified/closed |
| Decisions | `DESIGN_CLARIFICATIONS.md` | When debating approaches |

## CI Enforcement

Doc-code coupling enforced via `scripts/doc_coupling.yaml`. Run:

```bash
python scripts/check_doc_coupling.py --suggest
```
