# Project Meta Configuration

This directory contains project-specific meta-process configuration.

## Structure

```
meta/
└── acceptance_gates/                    # This project's feature definitions
    ├── acceptance_gates/CLAUDE.md       # How to use acceptance gates
    ├── acceptance_gates/ledger.yaml     # Ledger feature scope
    ├── acceptance_gates/escrow.yaml     # Escrow feature scope
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
- Features create claim scopes (only one CC can claim a feature at a time)
- The `shared.yaml` file defines cross-cutting files with no claim conflicts

See `acceptance_gates/CLAUDE.md` for details.

## Key Commands

```bash
# List available features (claim scopes)
python scripts/check_claims.py --list-features

# Claim a feature before working on it
python scripts/check_claims.py --claim --feature ledger --task "Fix bug"

# Check current claims
python scripts/check_claims.py --list
```

## Related

- `meta-process/patterns/13_acceptance-gate-driven-development.md` - Full pattern
- `meta-process/patterns/18_claim-system.md` - How claims work
- `CLAUDE.md` (root) - Project workflow overview
