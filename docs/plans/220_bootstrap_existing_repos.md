# Plan 220: Bootstrap for Existing Repos

**Status:** ✅ Complete
**Phase:** 4 of 5 (Meta-Process Improvements)
**Depends on:**
- Plan #215 (Unified Documentation Graph) - Complete
- Plan #218 (Configurable Weight) - Complete
**Blocked by:** None
**Completed:** 2026-01-26

## Implementation Evidence

- `scripts/bootstrap_meta_process.py` - Bootstrap script (400+ lines)
- `tests/unit/test_bootstrap.py` - 16 unit tests (all pass)

### Core Features

The bootstrap script provides:
- **Repo analysis** (`--analyze`): Detect structure, suggest couplings/ADRs
- **Initialization** (`--init`): Create starter meta-process files at any weight
- **Progress tracking** (`--progress`): Show compliance score and recommendations

### Usage
```bash
# Analyze repo structure
python scripts/bootstrap_meta_process.py --analyze

# Initialize at light weight
python scripts/bootstrap_meta_process.py --init --weight light

# Check progress toward full adoption
python scripts/bootstrap_meta_process.py --progress
```

## Problem

The meta-process is designed for greenfield projects where plans, ADRs, and docs are created alongside code. Bootstrapping an existing repo is different:

1. **No existing ADRs**: Decisions were made but not documented
2. **No plans**: Code exists without gap tracking
3. **No relationships.yaml**: No doc-code coupling defined
4. **Overwhelming to start**: Can't immediately enforce everything

Need a gradual onboarding path that:
- Generates starter configuration from existing structure
- Starts at `minimal` or `light` weight
- Provides guidance on what to document first
- Tracks progress toward full compliance

## Solution

Create a bootstrap script and onboarding process:

```bash
# Bootstrap existing repo
python scripts/bootstrap_meta_process.py --analyze
python scripts/bootstrap_meta_process.py --init
```

## Implementation

### 1. Repo analysis script

```python
# scripts/bootstrap_meta_process.py
"""Bootstrap meta-process for existing repos."""

import os
from pathlib import Path
from collections import defaultdict

def analyze_repo() -> dict:
    """Analyze existing repo structure."""
    analysis = {
        "has_docs": Path("docs").exists(),
        "has_tests": Path("tests").exists(),
        "has_src": Path("src").exists(),
        "file_count": 0,
        "test_count": 0,
        "doc_count": 0,
        "suggested_couplings": [],
        "suggested_adrs": [],
    }

    # Count files
    for ext in ["*.py", "*.ts", "*.js", "*.go"]:
        analysis["file_count"] += len(list(Path(".").rglob(ext)))

    # Count tests
    analysis["test_count"] = len(list(Path(".").rglob("test_*.py")))
    analysis["test_count"] += len(list(Path(".").rglob("*_test.py")))

    # Count docs
    analysis["doc_count"] = len(list(Path(".").rglob("*.md")))

    # Suggest couplings based on naming conventions
    analysis["suggested_couplings"] = suggest_couplings()

    # Suggest ADRs based on common architectural patterns
    analysis["suggested_adrs"] = suggest_adrs()

    return analysis

def suggest_couplings() -> list[dict]:
    """Suggest doc-code couplings based on structure."""
    couplings = []

    # Pattern: docs/X.md <-> src/X/
    if Path("docs").exists() and Path("src").exists():
        for doc in Path("docs").glob("*.md"):
            stem = doc.stem
            if Path(f"src/{stem}").exists():
                couplings.append({
                    "sources": [f"src/{stem}/**/*.py"],
                    "docs": [str(doc)],
                    "description": f"Auto-detected: {stem} module"
                })

    # Pattern: README.md <-> main entry point
    if Path("README.md").exists():
        for entry in ["main.py", "run.py", "app.py", "src/main.py"]:
            if Path(entry).exists():
                couplings.append({
                    "sources": [entry],
                    "docs": ["README.md"],
                    "description": "Main entry point"
                })

    return couplings

def suggest_adrs() -> list[dict]:
    """Suggest ADRs based on detected patterns."""
    suggestions = []

    # Detect common patterns that warrant ADRs
    patterns = [
        ("requirements.txt", "Dependency management approach"),
        ("Dockerfile", "Containerization strategy"),
        ("docker-compose.yml", "Service orchestration"),
        (".github/workflows", "CI/CD approach"),
        ("alembic.ini", "Database migration strategy"),
        ("pytest.ini", "Testing strategy"),
    ]

    for pattern, description in patterns:
        if Path(pattern).exists():
            suggestions.append({
                "title": description,
                "detected_from": pattern,
                "priority": "medium"
            })

    return suggestions
```

### 2. Init script

```python
def init_meta_process(weight: str = "light"):
    """Initialize meta-process files."""

    # Create meta-process.yaml with specified weight
    meta_process = {
        "weight": weight,
        "bootstrap": {
            "date": datetime.now().isoformat(),
            "initial_weight": weight,
        }
    }
    write_yaml("meta-process.yaml", meta_process)

    # Create starter relationships.yaml
    relationships = {
        "adrs": {},
        "governance": [],
        "couplings": suggest_couplings(),
    }
    write_yaml("scripts/relationships.yaml", relationships)

    # Create docs/plans/ if needed
    Path("docs/plans").mkdir(parents=True, exist_ok=True)

    # Create starter CLAUDE.md if not exists
    if not Path("CLAUDE.md").exists():
        create_starter_claude_md()

    # Create docs/adr/ if not exists
    Path("docs/adr").mkdir(parents=True, exist_ok=True)

    print(f"Initialized meta-process at weight: {weight}")
    print("Next steps:")
    print("  1. Review scripts/relationships.yaml")
    print("  2. Create first ADR for your core architecture")
    print("  3. Run: python scripts/bootstrap_meta_process.py --progress")
```

### 3. Progress tracking

```python
def show_progress():
    """Show progress toward full meta-process adoption."""
    metrics = {
        "adrs_documented": count_adrs(),
        "couplings_defined": count_couplings(),
        "plans_created": count_plans(),
        "weight": get_current_weight(),
        "compliance_score": calculate_compliance(),
    }

    print("Meta-Process Adoption Progress")
    print("=" * 40)
    print(f"Current weight: {metrics['weight']}")
    print(f"ADRs documented: {metrics['adrs_documented']}")
    print(f"Couplings defined: {metrics['couplings_defined']}")
    print(f"Plans created: {metrics['plans_created']}")
    print(f"Compliance score: {metrics['compliance_score']}%")
    print()
    print("Recommendations:")
    for rec in get_recommendations(metrics):
        print(f"  - {rec}")

def get_recommendations(metrics: dict) -> list[str]:
    """Generate recommendations for next steps."""
    recs = []

    if metrics["adrs_documented"] == 0:
        recs.append("Create your first ADR documenting a key decision")

    if metrics["couplings_defined"] < 3:
        recs.append("Add more doc-code couplings to relationships.yaml")

    if metrics["weight"] == "minimal" and metrics["compliance_score"] > 50:
        recs.append("Consider upgrading to 'light' weight")

    if metrics["weight"] == "light" and metrics["compliance_score"] > 75:
        recs.append("Consider upgrading to 'medium' weight")

    return recs
```

### 4. Weight upgrade assistant

```python
def check_upgrade_readiness(target_weight: str) -> dict:
    """Check if repo is ready to upgrade weight level."""
    current = get_current_weight()
    issues = []

    if target_weight == "medium" and current == "light":
        # Check requirements for medium
        if count_adrs() < 1:
            issues.append("Need at least 1 ADR for medium weight")
        if count_couplings() < 5:
            issues.append("Need at least 5 couplings for medium weight")

    if target_weight == "heavy" and current == "medium":
        # Check requirements for heavy
        if not all_couplings_verified():
            issues.append("All couplings must be verified for heavy weight")
        if not governance_headers_complete():
            issues.append("All governed files need governance headers")

    return {
        "ready": len(issues) == 0,
        "issues": issues,
        "current_weight": current,
        "target_weight": target_weight,
    }
```

## Test Plan

### Unit Tests
```python
# tests/unit/test_bootstrap.py

def test_analyze_empty_repo():
    """Analyze repo with minimal structure"""

def test_analyze_full_repo():
    """Analyze repo with docs, tests, src"""

def test_suggest_couplings():
    """Coupling suggestions based on structure"""

def test_suggest_adrs():
    """ADR suggestions based on detected patterns"""

def test_init_creates_files():
    """Init creates necessary files"""

def test_progress_tracking():
    """Progress metrics calculated correctly"""

def test_upgrade_readiness():
    """Upgrade readiness checks work"""
```

### Integration Tests
```python
def test_bootstrap_on_real_repo():
    """Run bootstrap on actual codebase"""

def test_progress_on_real_repo():
    """Progress tracking on actual codebase"""
```

## Acceptance Criteria

- [ ] `--analyze` shows repo structure analysis
- [ ] `--init` creates starter meta-process files
- [ ] Suggested couplings generated from structure
- [ ] Suggested ADRs generated from patterns
- [ ] `--progress` shows adoption progress
- [ ] Upgrade readiness checker works
- [ ] Documentation for onboarding process
- [ ] Unit tests pass
- [ ] Works on a fresh clone of our repo

## Files to Create/Modify

- `scripts/bootstrap_meta_process.py` - New: main bootstrap script
- `docs/ONBOARDING.md` - New: onboarding guide
- `tests/unit/test_bootstrap.py` - New test file
- `CLAUDE.md` - Document bootstrap process

## Ambiguities

1. **Minimum viable ADRs**: What decisions MUST be documented for `medium` weight? Some suggestions:
   - Core architecture (how code is organized)
   - Testing strategy
   - Dependency management
   This is somewhat subjective.

2. **Coupling detection heuristics**: The automatic coupling detection is best-effort. May generate false positives. Users should review and edit.

3. **Weight upgrade thresholds**: What compliance score triggers upgrade recommendation? Current thinking:
   - 50% → suggest `light`
   - 75% → suggest `medium`
   - 90% → suggest `heavy`
   These are arbitrary and may need tuning.

4. **Partial adoption**: Can teams adopt only parts of meta-process? E.g., just doc-coupling without plans? Weight system sort of supports this but not explicitly.

5. **Multi-language repos**: Current analysis is Python-focused. TypeScript, Go, etc. would need language-specific analysis. Start with Python, add others later.

6. **Monorepo support**: Large monorepos might want per-package meta-process settings. Not addressed here - could be follow-up plan.

7. **Team size considerations**: Larger teams might need heavier enforcement sooner. Should team size factor into recommendations?

8. **Legacy code carve-outs**: Should there be a way to exclude legacy directories from enforcement? E.g., "src/legacy/ is exempt until refactored". Could add to meta-process.yaml:
   ```yaml
   exempt:
     - src/legacy/**
     - vendor/**
   ```
