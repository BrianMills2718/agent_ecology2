# Documentation Directory

All extended documentation lives here. Root CLAUDE.md has the overview.

## Structure

```
docs/
├── adr/            # Architecture Decision Records (immutable)
├── architecture/
│   ├── current/    # What IS implemented (source of truth)
│   └── target/     # What we WANT (aspirational)
├── meta/           # Reusable process patterns
├── plans/          # Gap tracking + implementation plans
├── features/       # Feature-specific documentation
├── GLOSSARY.md     # Canonical terminology
├── DESIGN_CLARIFICATIONS.md  # Decision rationale archive
└── SECURITY.md     # Security model
```

## Key Files

| File | Purpose | When to Update |
|------|---------|----------------|
| `adr/` | Architecture Decision Records | New architectural decisions |
| `meta/` | Reusable process patterns | New patterns identified |
| `GLOSSARY.md` | Canonical terms (scrip, principal, tick) | New concepts added |
| `DESIGN_CLARIFICATIONS.md` | WHY decisions were made | Architecture discussions |
| `SECURITY.md` | Security model and boundaries | Security changes |

## Doc Types

| Type | Location | Updates |
|------|----------|---------|
| Current reality | `architecture/current/` | After code changes |
| Future vision | `architecture/target/` | Architecture decisions |
| ADRs | `adr/` | New architectural decisions (immutable once accepted) |
| Process patterns | `meta/` | Reusable patterns identified |
| Implementation | `plans/` | Gap identified/closed |
| Decisions | `DESIGN_CLARIFICATIONS.md` | When debating approaches |

## CI Enforcement

**Doc-code coupling:** `scripts/doc_coupling.yaml`
```bash
python scripts/check_doc_coupling.py --suggest
```

**ADR governance:** `scripts/governance.yaml`
```bash
python scripts/sync_governance.py --check
```
