# Pattern: Feature Linkage

How to structure relationships between ADRs, features, code, tests, and documentation for full traceability.

## Complete Linkage Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              CURRENT STATE (Problematic)                         │
└─────────────────────────────────────────────────────────────────────────────────┘

    ┌───────────┐                                           ┌───────────┐
    │   ADRs    │                                           │   Plans   │
    │ (5 exist) │                                           │(34 exist) │
    └─────┬─────┘                                           └─────┬─────┘
          │                                                       │
          │ governance.yaml                                       │ (weak soft
          │ (SPARSE: only 5 files!)                               │  coupling)
          ▼                                                       ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                           SOURCE FILES (src/)                            │
    │                                                                          │
    │   ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
    │   │ledger.py │ │escrow.py │ │runner.py │ │agent.py  │ │ ??? .py  │     │
    │   │ mapped   │ │ mapped   │ │NOT mapped│ │NOT mapped│ │NOT mapped│     │
    │   └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
    └─────────────────────────────────────────────────────────────────────────┘
          │
          │ doc_coupling.yaml (MANUAL, incomplete)
          ▼
    ┌───────────┐         ┌───────────┐
    │   DOCS    │    ?    │   TESTS   │  ← No mapping to features/plans
    └───────────┘         └───────────┘


┌─────────────────────────────────────────────────────────────────────────────────┐
│                              OPTIMAL STATE (New)                                 │
└─────────────────────────────────────────────────────────────────────────────────┘

                         ┌─────────────────────────────────┐
                         │         features.yaml           │
                         │    (SINGLE SOURCE OF TRUTH)     │
                         └────────────────┬────────────────┘
                                          │
           ┌──────────────────────────────┼──────────────────────────────┐
           │                              │                              │
           ▼                              ▼                              ▼
    ┌─────────────┐               ┌─────────────┐               ┌─────────────┐
    │  FEATURE:   │               │  FEATURE:   │               │  FEATURE:   │
    │   escrow    │               │   ledger    │               │rate_limiting│
    └──────┬──────┘               └──────┬──────┘               └──────┬──────┘
           │                              │                              │
           ▼                              ▼                              ▼
    ┌─────────────────────────────────────────────────────────────────────────┐
    │                         FEATURE CONTENTS                                 │
    │                                                                          │
    │   problem         → WHY this feature exists                              │
    │   acceptance_criteria → Given/When/Then specs (LOCKED before impl)       │
    │   out_of_scope    → Explicit exclusions (prevents AI drift)              │
    │   adrs            → [1, 3] constraints from architecture decisions       │
    │   code            → [escrow.py, ...] source files                        │
    │   tests           → [test_escrow.py, ...] verification                   │
    │   docs            → [genesis.md, ...] documentation                      │
    └─────────────────────────────────────────────────────────────────────────┘
                                          │
                    ┌─────────────────────┬┴───────────────────┐
                    │                     │                    │
                    ▼                     ▼                    ▼
           ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
           │   DERIVED:   │      │   DERIVED:   │      │   DERIVED:   │
           │  governance  │      │ doc-coupling │      │ test-mapping │
           │ (file → ADR) │      │ (file → doc) │      │(file → test) │
           └──────────────┘      └──────────────┘      └──────────────┘


                         QUERIES NOW POSSIBLE
    ┌─────────────────────────────────────┬───────────────────────────────┐
    │  QUERY                              │  LOOKUP PATH                  │
    ├─────────────────────────────────────┼───────────────────────────────┤
    │  "What ADRs apply to escrow.py?"    │  file → feature → adrs        │
    │  "What tests cover escrow?"         │  feature → tests              │
    │  "What feature owns runner.py?"     │  file → feature               │
    │  "Is escrow fully tested?"          │  feature.tests all pass?      │
    │  "What docs need update?"           │  file → feature → docs        │
    │  "What does ADR-1 govern?"          │  reverse: adrs → features     │
    └─────────────────────────────────────┴───────────────────────────────┘
```

## Problem

### Sparse, Disconnected Mappings

See "CURRENT STATE" in the diagram above. Key issues:

- `governance.yaml` only maps ~5 files to ADRs
- Most source files have NO ADR mapping
- `doc_coupling.yaml` is manual and incomplete
- Plans are administrative, not linked to code
- No Feature concept linking code + tests + docs + ADRs
- Tests have no mapping to features or plans

### What's Missing

| Query | Can Answer? |
|-------|-------------|
| "What ADRs apply to this file?" | Only if file is in sparse mapping |
| "What tests cover this feature?" | No |
| "Which plan owns this file?" | No |
| "Is this feature fully tested?" | No |
| "What docs need updating if I change X?" | Partial |

## Solution

### Feature as Central Entity

See "OPTIMAL STATE" in the diagram above. **Feature** becomes the single source of truth connecting:

- **ADRs** - Architectural constraints
- **Code** - Source files implementing the feature
- **Tests** - Verification that feature works
- **Docs** - Documentation explaining the feature

All other mappings (governance, doc-coupling, test-mapping) are **derived** from features.yaml.

### Features.yaml Schema

```yaml
features:
  escrow:
    description: "Trustless artifact trading"

    # Constraints
    adrs: [1, 3]  # ADR-0001, ADR-0003

    # Implementation
    code:
      - src/world/escrow.py
      - src/world/contracts/escrow_contract.py

    # Verification
    tests:
      - tests/unit/test_escrow.py
      - tests/e2e/test_escrow.py

    # Documentation
    docs:
      - docs/architecture/current/genesis_artifacts.md

  rate_limiting:
    description: "Token bucket rate limiting for resources"
    adrs: [2]
    code:
      - src/world/rate_tracker.py
    tests:
      - tests/unit/test_rate_tracker.py
    docs:
      - docs/architecture/current/resources.md

  # ... all features
```

## Derived Mappings

From `features.yaml`, derive all other mappings:

### File → ADR (replaces governance.yaml)

```python
def get_adrs_for_file(filepath: str) -> list[int]:
    """Given a file, return which ADRs govern it."""
    for feature in features.values():
        if filepath in feature['code']:
            return feature['adrs']
    return []
```

### File → Doc (replaces doc_coupling.yaml)

```python
def get_docs_for_file(filepath: str) -> list[str]:
    """Given a file, return which docs should be updated."""
    for feature in features.values():
        if filepath in feature['code']:
            return feature['docs']
    return []
```

### Feature → Tests

```python
def get_tests_for_feature(feature_name: str) -> list[str]:
    """Given a feature, return its tests."""
    return features[feature_name]['tests']
```

### File → Feature (reverse lookup)

```python
def get_feature_for_file(filepath: str) -> str | None:
    """Given a file, return which feature owns it."""
    for name, feature in features.items():
        if filepath in feature['code']:
            return name
    return None
```

## Queries Now Possible

| Query | How |
|-------|-----|
| "What ADRs apply to this file?" | `get_adrs_for_file(path)` |
| "What tests cover this feature?" | `get_tests_for_feature(name)` |
| "What feature owns this file?" | `get_feature_for_file(path)` |
| "Is this feature fully tested?" | Check all tests in feature pass |
| "What docs need updating?" | `get_docs_for_file(path)` |
| "What files does ADR-X govern?" | Reverse lookup through features |

## Handling Edge Cases

### Shared Utilities

Files used by multiple features:

```yaml
shared:
  utils:
    description: "Shared utility functions"
    code:
      - src/utils.py
      - src/common/helpers.py
    # No specific ADRs - inherits from all features that use it
    # Tests in unit tests, not feature tests
    tests:
      - tests/unit/test_utils.py
```

### Code Not Yet Assigned

Temporary state during migration:

```yaml
unassigned:
  description: "Code not yet assigned to a feature"
  code:
    - src/legacy/old_module.py
  # Flagged in CI as needing assignment
```

### Multiple Features for One File

If a file legitimately belongs to multiple features (rare):

```yaml
ledger:
  code:
    - src/world/ledger.py  # Primary

escrow:
  code:
    - src/world/ledger.py  # Also uses (secondary)
```

Resolution: Primary feature's ADRs apply. Both features' tests must pass.

## Migration Path

### From Current State

1. **Audit existing code** - List all files in `src/`
2. **Identify features** - Group files by capability
3. **Create features.yaml** - Define features with code mappings
4. **Add ADR mappings** - Which ADRs apply to each feature
5. **Add test mappings** - Which tests verify each feature
6. **Deprecate old configs** - Replace governance.yaml, doc_coupling.yaml

### Validation Script

```bash
# Check all src/ files are assigned to a feature
python scripts/check_feature_coverage.py

# Output:
# ✓ src/world/ledger.py -> feature:ledger
# ✓ src/world/escrow.py -> feature:escrow
# ✗ src/world/orphan.py -> UNASSIGNED
```

## Files

| File | Purpose |
|------|---------|
| `features.yaml` | Single source of truth |
| `scripts/derive_governance.py` | Generate governance.yaml from features |
| `scripts/derive_doc_coupling.py` | Generate doc_coupling.yaml from features |
| `scripts/check_feature_coverage.py` | Ensure all code assigned |

## Benefits

| Before | After |
|--------|-------|
| Sparse ADR mapping | Complete coverage via features |
| Manual doc_coupling.yaml | Derived from features |
| "What owns this file?" - unknown | Feature lookup |
| "Is feature tested?" - unknown | Feature.tests check |
| Plans as organization | Features as organization, plans as tasks |

## Related Patterns

- [Feature-Driven Development](feature-driven-development.md) - The complete meta-process
- [ADR Governance](adr-governance.md) - Now derived from features
- [Doc-Code Coupling](doc-code-coupling.md) - Now derived from features
- [Documentation Graph](documentation-graph.md) - Features as nodes

## Origin

Identified during meta-process design when analyzing why ADR conformance checking would fail - the linkage from files to ADRs was too sparse to be useful. Feature-centric organization provides complete coverage.
