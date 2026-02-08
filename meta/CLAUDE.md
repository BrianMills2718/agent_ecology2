# Project Meta Configuration

This directory contains project-specific meta-process configuration.

## Structure

```
meta/
└── acceptance_gates/                    # This project's feature definitions
    ├── acceptance_gates/CLAUDE.md       # How to use acceptance gates
    ├── acceptance_gates/ledger.yaml     # Ledger feature scope
    ├── acceptance_gates/ledger.yaml     # Ledger feature scope
    └── ...                              # Other project features
```

## Portable Template

The reusable meta-process framework is in `meta-process/`:

```
meta-process/
├── meta-process/README.md      # How to use the framework
├── meta-process/install.sh     # Install to new project
├── meta-process/patterns/      # Pattern documentation (26 patterns)
├── meta-process/scripts/       # Portable scripts
├── meta-process/hooks/         # Git + Claude Code hooks
├── meta-process/ci/            # CI workflow templates
└── meta-process/templates/     # Starter file templates
```

To use the meta-process in a new project:
```bash
./meta-process/install.sh /path/to/new/project
```

## This Project's Gates

The `acceptance_gates/` directory defines feature scopes for this project:
- Each `.yaml` file defines a feature with its code files
- The `shared.yaml` file defines cross-cutting files

See `acceptance_gates/CLAUDE.md` for details.

## Related

- `meta-process/patterns/13_acceptance-gate-driven-development.md` - Full pattern
- `CLAUDE.md` (root) - Project workflow overview
