# Features Directory

Feature definition files that map code, tests, and docs to logical features.

## Purpose

Features are the unit of organization for:
- **Claims** - When you claim a feature, you claim its code files
- **Testing** - Feature acceptance criteria define required tests
- **Documentation** - Each feature links to its docs
- **ADR governance** - Features inherit ADR constraints

## File Format

Each `*.yaml` file defines a feature:

```yaml
feature: feature_name
planning_mode: autonomous | guided | detailed

problem: |
  What problem this feature solves

out_of_scope:
  - "What this feature does NOT handle"

acceptance_criteria:
  - id: AC-1
    scenario: "Description"
    category: happy_path | error_case | edge_case
    given: [...]
    when: "..."
    then: [...]
    locked: true  # Cannot change without human review

adrs:
  - ADR-NNNN  # ADRs that govern this feature

code:
  - src/path/to/file.py

tests:
  - tests/path/to/test.py

docs:
  - docs/path/to/doc.md
```

## Key Commands

```bash
# List features and their claims
python scripts/check_claims.py --list-features

# Check feature test coverage
python scripts/check_feature_coverage.py

# Validate a feature spec
python scripts/validate_spec.py --feature ledger
```

## Planning Modes

| Mode | Human Involvement | Use When |
|------|-------------------|----------|
| `autonomous` | Tests only | Mature, well-understood feature |
| `guided` | Review changes | New feature, moderate risk |
| `detailed` | Review each step | High risk, architectural changes |

## Special Features

- `shared.yaml` - Cross-cutting files (config, fixtures) - no claim conflicts
- `meta-process-tooling.yaml` - The tooling that enforces features

## Related Patterns

See `docs/meta/13_feature-driven-development.md` for the full pattern.
