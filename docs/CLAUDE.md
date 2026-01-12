# Documentation Directory

All extended documentation lives here. Root CLAUDE.md has the overview.

## Structure

```
docs/
├── architecture/
│   ├── current/    # What IS implemented (source of truth)
│   └── target/     # What we WANT (aspirational)
├── plans/          # Gap tracking + implementation plans
├── features/       # Feature-specific documentation
├── GLOSSARY.md     # Canonical terminology
├── DESIGN_CLARIFICATIONS.md  # Decision rationale archive
└── SECURITY.md     # Security model
```

## Key Files

| File | Purpose | When to Update |
|------|---------|----------------|
| `GLOSSARY.md` | Canonical terms (scrip, principal, tick) | New concepts added |
| `DESIGN_CLARIFICATIONS.md` | WHY decisions were made | Architecture discussions |
| `SECURITY.md` | Security model and boundaries | Security changes |

## Doc Types

| Type | Location | Updates |
|------|----------|---------|
| Current reality | `architecture/current/` | After code changes |
| Future vision | `architecture/target/` | Architecture decisions |
| Implementation | `plans/` | Gap identified/closed |
| Decisions | `DESIGN_CLARIFICATIONS.md` | When debating approaches |

## CI Enforcement

Doc-code coupling enforced via `scripts/doc_coupling.yaml`. Run:

```bash
python scripts/check_doc_coupling.py --suggest
```
