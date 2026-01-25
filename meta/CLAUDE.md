# Project Meta Configuration

This directory contains project-specific meta-process configuration.

## Structure

```
meta/
└── acceptance_gates/     # This project's feature definitions
    ├── CLAUDE.md         # How to use acceptance gates
    ├── ledger.yaml       # Ledger feature scope
    ├── escrow.yaml       # Escrow feature scope
    └── ...               # Other project features
```

## Portable Template

The reusable meta-process framework is in `meta-process/`:

```
meta-process/
├── README.md             # How to use the framework
├── install.sh            # Install to new project
├── patterns/             # Pattern documentation (26 patterns)
├── scripts/              # Portable scripts
├── hooks/                # Git + Claude Code hooks
├── ci/                   # CI workflow templates
└── templates/            # Starter file templates
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
