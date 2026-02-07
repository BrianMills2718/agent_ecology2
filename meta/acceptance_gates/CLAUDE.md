# Features Directory

## Core Purpose

**Features are E2E acceptance gates.**

A feature is COMPLETE when its acceptance criteria pass with **real (non-mocked) integration**. Not when code is written. Not when unit tests pass. When real E2E works with no mocks.

```
Feature: escrow
├── AC-1: Deposit works       ← Must pass with NO MOCKS
├── AC-2: Purchase works      ← Must pass with NO MOCKS
├── AC-3: Cancellation works  ← Must pass with NO MOCKS
│
└── DONE when: pytest tests/e2e/test_real_e2e.py --run-external passes
```

## Features vs Plans

| Concept | Purpose | Done When |
|---------|---------|-----------|
| **Feature** | E2E acceptance gate | Real LLM E2E tests pass |
| **Plan** | Unit of work toward a feature | Code done, unit tests pass |

- Multiple **plans** contribute to one **feature**
- Plans can be "complete" while feature is still incomplete
- Feature completion = the REAL checkpoint

## Why This Matters

Unit tests can pass with mocks. Integration tests can pass with mocks. Only real E2E with **no mocks at all** proves the system actually works.

Features define these real checkpoints:
- "Escrow actually works when agents trade"
- "Rate limiting actually throttles LLM calls"
- "Contracts actually execute agent code"

## File Format

```yaml
feature: feature_name

# What problem this solves (plain English)
problem: |
  Agents need to trade artifacts without trusting each other.

# What this feature does NOT handle
out_of_scope:
  - "Multi-party trades"
  - "Partial payments"

# E2E acceptance criteria - MUST pass with real LLM
acceptance_criteria:
  - id: AC-1
    scenario: "Successful artifact sale"
    category: happy_path
    given:
      - "Seller owns artifact X"
      - "Buyer has sufficient scrip"
    when: "Buyer purchases via escrow"
    then:
      - "Buyer owns artifact"
      - "Seller received payment"
    locked: true  # Cannot weaken after commit

# Implementation mapping
adrs: [ADR-0001]           # Architectural constraints
code: [src/world/genesis.py]
tests: [tests/e2e/test_escrow_e2e.py]  # Real E2E tests
docs: [docs/architecture/current/genesis_artifacts.md]
```

## Verification

```bash
# Check if a feature's E2E tests pass (REAL LLM)
pytest tests/e2e/test_real_e2e.py -v --run-external -k "escrow"

# This is what "feature complete" means
# NOT just: pytest tests/unit/test_escrow.py
# NOT just: pytest tests/integration/test_escrow.py
```

## Relationship to Plans

Plans are work toward features:

```
Feature: escrow (E2E gate)
│
├── Plan #9: Basic deposit/purchase    ← Implements AC-1, AC-2
│   └── Status: Complete
│
├── Plan #15: Add cancellation         ← Implements AC-3
│   └── Status: Complete
│
└── Feature Status: ???
    └── Run real E2E to find out!
```

All plans complete ≠ feature complete. Real E2E must pass.

## Locked Acceptance Criteria

The `locked: true` flag prevents weakening criteria after commit:

- CC writes acceptance criteria
- Human reviews and approves
- Criteria committed with `locked: true`
- CC cannot modify locked criteria to make tests easier
- If tests fail, CC must fix code, not weaken tests

## Commands

```bash
# List features
python scripts/check_claims.py --list-features

# Run feature's real E2E tests
pytest tests/e2e/ -v --run-external -k "feature_name"
```

## Planning Modes

| Mode | When to Use |
|------|-------------|
| `autonomous` | Mature feature, low risk, CC works independently |
| `guided` | New feature, human reviews acceptance criteria |
| `detailed` | High risk, human reviews each step |

## Key Files

- `shared.yaml` - Cross-cutting files (no claim conflicts)
- `*.yaml` - One file per feature

## Related

- `meta/patterns/13_acceptance-gate-driven-development.md` - Full pattern details
- `meta/patterns/17_verification-enforcement.md` - How completion is verified
