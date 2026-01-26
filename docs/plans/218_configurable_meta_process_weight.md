# Plan 218: Configurable Meta-Process Weight

**Status:** ✅ Complete
**Phase:** 2b of 5 (Meta-Process Improvements)
**Depends on:** Plan #215 (Unified Documentation Graph) - Complete
**Blocked by:** None (can be done in parallel with Plan #217)
**Completed:** 2026-01-26

## Implementation Evidence

- `scripts/meta_process_config.py` - Core weight configuration module (150+ lines)
- `meta-process.yaml` - Added `weight` setting and `overrides` section
- `scripts/check_doc_coupling.py` - Added `--weight-aware` flag
- `tests/unit/test_meta_process_weight.py` - 24 unit tests (all pass)

### Core Implementation

The weight system provides 4 levels (MINIMAL < LIGHT < MEDIUM < HEAVY) with:
- Per-check minimum weight requirements (CHECK_WEIGHTS dict)
- Per-check overrides (strict/disabled) in meta-process.yaml
- CLI for checking weight status: `python scripts/meta_process_config.py`
- Scripts can use `check_enabled(check_name)` to respect weight

## Problem

The current meta-process is one-size-fits-all. Some projects need heavy enforcement (enterprise, regulated), while others want minimal friction (prototypes, small projects). Users should be able to configure how strict the meta-process is.

Additionally, when bootstrapping an existing repo, starting with heavy enforcement would be overwhelming. Need a gradual ramp-up path.

## Solution

Add a `weight` setting to `meta-process.yaml` that controls which checks run:

```yaml
# meta-process.yaml
weight: medium  # heavy | medium | light | minimal
```

## Weight Levels

| Check | Heavy | Medium | Light | Minimal |
|-------|-------|--------|-------|---------|
| Plan validation (pre-impl) | ✓ | ✓ | ✓ | ✓ |
| Plan required for commits | ✓ | ✓ | ✓ | - |
| Doc-coupling (strict/blocking) | ✓ | ✓ | - | - |
| Doc-coupling (warning only) | ✓ | ✓ | ✓ | - |
| ADR governance headers | ✓ | ✓ | - | - |
| Context injection on read | ✓ | ✓ | ✓ | - |
| Bidirectional prompts | ✓ | - | - | - |
| Symbol-level checks | ✓ | - | - | - |
| Test requirements | ✓ | ✓ | ✓ | - |
| Claim system | ✓ | ✓ | - | - |
| Worktree enforcement | ✓ | ✓ | - | - |

### Weight Descriptions

- **Heavy**: Full enforcement. For mature projects, regulated environments, multi-contributor. All checks blocking.
- **Medium**: Balanced. Most checks run but less blocking. Good default for active development.
- **Light**: Low friction. Warnings instead of blocks. For prototypes or onboarding.
- **Minimal**: Almost nothing. Just plan validation. For quick experiments or legacy code.

## Implementation

### 1. Config schema

```yaml
# meta-process.yaml
weight: medium

# Optional per-check overrides
overrides:
  doc_coupling: strict    # Force strict even at light weight
  bidirectional: disabled # Disable even at heavy weight
```

### 2. Weight-aware check functions

```python
# scripts/meta_process_config.py

from enum import IntEnum
from pathlib import Path
import yaml

class Weight(IntEnum):
    MINIMAL = 0
    LIGHT = 1
    MEDIUM = 2
    HEAVY = 3

def get_weight() -> Weight:
    """Get configured meta-process weight."""
    config_path = Path("meta-process.yaml")
    if not config_path.exists():
        return Weight.MEDIUM  # Default

    with open(config_path) as f:
        config = yaml.safe_load(f)

    weight_str = config.get("weight", "medium").lower()
    return Weight[weight_str.upper()]

def check_enabled(check_name: str, min_weight: Weight) -> bool:
    """Check if a specific check is enabled at current weight."""
    weight = get_weight()

    # Check for override
    config = load_config()
    overrides = config.get("overrides", {})
    if check_name in overrides:
        override = overrides[check_name]
        if override == "disabled":
            return False
        if override == "strict":
            return True

    return weight >= min_weight

# Example usage in scripts:
if check_enabled("doc_coupling_strict", Weight.MEDIUM):
    run_strict_doc_coupling()
elif check_enabled("doc_coupling_warning", Weight.LIGHT):
    run_warning_doc_coupling()
```

### 3. Update existing scripts

Each script checks weight before running:

```python
# In check_doc_coupling.py
from meta_process_config import check_enabled, Weight

def main():
    if args.strict:
        if not check_enabled("doc_coupling_strict", Weight.MEDIUM):
            print("Doc coupling strict check disabled at current weight")
            return 0
    # ... rest of script
```

### 4. CI integration

```yaml
# .github/workflows/ci.yml
- name: Run meta-process checks
  run: |
    # Weight is read from meta-process.yaml
    python scripts/check_doc_coupling.py --weight-aware
    python scripts/sync_governance.py --weight-aware
```

## Test Plan

### Unit Tests
```python
# tests/unit/test_meta_process_weight.py

def test_weight_parsing():
    """Parse weight from config file"""

def test_default_weight():
    """Default to medium when no config"""

def test_check_enabled_at_weight():
    """Checks correctly enabled/disabled per weight"""

def test_override_enables_check():
    """Override can force-enable a check"""

def test_override_disables_check():
    """Override can force-disable a check"""

def test_heavy_enables_all():
    """Heavy weight enables all checks"""

def test_minimal_disables_most():
    """Minimal weight disables most checks"""
```

### Integration Tests
```python
def test_doc_coupling_respects_weight():
    """Doc coupling script respects weight setting"""

def test_ci_respects_weight():
    """CI workflow respects weight setting"""
```

## Acceptance Criteria

- [x] `meta-process.yaml` weight setting parsed
- [x] Four weight levels: heavy, medium, light, minimal
- [x] Per-check overrides work
- [x] Existing scripts check weight before running (check_doc_coupling.py)
- [x] Default weight is medium
- [x] CI respects weight setting (via --weight-aware flag)
- [x] Unit tests pass (24 tests)
- [ ] Documentation updated (deferred - CLAUDE.md can be updated separately)

## Files to Create/Modify

- `scripts/meta_process_config.py` - New: weight config logic
- `meta-process.yaml` - Add weight setting
- `scripts/check_doc_coupling.py` - Check weight
- `scripts/sync_governance.py` - Check weight
- `scripts/validate_plan.py` - Check weight
- `.github/workflows/ci.yml` - Weight-aware checks
- `tests/unit/test_meta_process_weight.py` - New test file
- `CLAUDE.md` - Document weight configuration

## Ambiguities

1. **Default weight for new repos**: Should new repos start at `medium` or `light`? Leaning toward `medium` as it's balanced.

2. **Weight in CI vs local**: Should CI always run at `heavy` regardless of config? Or respect the config? Leaning toward respecting config for consistency.

3. **Migration path**: When upgrading weight (light → medium), should there be a "dry run" mode that shows what would fail without blocking?

4. **Per-directory weight**: Some parts of a repo might need different weights (e.g., `src/` heavy, `scripts/` light). Is this needed? Leaning toward no for simplicity.

5. **Weight inheritance**: If a worktree has different weight than main, which applies? Probably worktree's local config.
