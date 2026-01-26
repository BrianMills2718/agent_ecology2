#!/usr/bin/env python3
"""Bootstrap meta-process for existing repos (Plan #220).

This script helps onboard existing codebases to the meta-process by:
1. Analyzing repo structure to suggest configurations
2. Creating starter files (meta-process.yaml, relationships.yaml, etc.)
3. Tracking progress toward full meta-process adoption

Usage:
    python scripts/bootstrap_meta_process.py --analyze      # Analyze repo
    python scripts/bootstrap_meta_process.py --init         # Create files
    python scripts/bootstrap_meta_process.py --init --weight light  # Start at light
    python scripts/bootstrap_meta_process.py --progress     # Show progress
"""

import argparse
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml


def analyze_repo() -> dict[str, Any]:
    """Analyze existing repo structure.

    Returns:
        Dict with repo analysis results.
    """
    analysis: dict[str, Any] = {
        "has_docs": Path("docs").exists(),
        "has_tests": Path("tests").exists(),
        "has_src": Path("src").exists(),
        "has_claude_md": Path("CLAUDE.md").exists(),
        "has_meta_process": Path("meta-process.yaml").exists(),
        "has_relationships": Path("scripts/relationships.yaml").exists(),
        "file_count": 0,
        "test_count": 0,
        "doc_count": 0,
        "suggested_couplings": [],
        "suggested_adrs": [],
        "detected_patterns": [],
    }

    # Count source files
    for ext in ["*.py", "*.ts", "*.js", "*.go", "*.rs", "*.java"]:
        analysis["file_count"] += len(list(Path(".").rglob(ext)))

    # Count tests
    analysis["test_count"] = len(list(Path(".").rglob("test_*.py")))
    analysis["test_count"] += len(list(Path(".").rglob("*_test.py")))
    analysis["test_count"] += len(list(Path(".").rglob("*.test.ts")))
    analysis["test_count"] += len(list(Path(".").rglob("*.test.js")))

    # Count docs
    analysis["doc_count"] = len(list(Path(".").rglob("*.md")))

    # Suggest couplings based on naming conventions
    analysis["suggested_couplings"] = suggest_couplings()

    # Suggest ADRs based on common architectural patterns
    analysis["suggested_adrs"] = suggest_adrs()

    # Detect architecture patterns
    analysis["detected_patterns"] = detect_patterns()

    return analysis


def suggest_couplings() -> list[dict[str, Any]]:
    """Suggest doc-code couplings based on structure."""
    couplings: list[dict[str, Any]] = []

    # Pattern: docs/X.md <-> src/X/
    if Path("docs").exists() and Path("src").exists():
        for doc in Path("docs").glob("*.md"):
            stem = doc.stem
            if Path(f"src/{stem}").is_dir():
                couplings.append({
                    "sources": [f"src/{stem}/**/*.py"],
                    "docs": [str(doc)],
                    "description": f"Auto-detected: {stem} module",
                })

    # Pattern: README.md <-> main entry point
    if Path("README.md").exists():
        for entry in ["main.py", "run.py", "app.py", "src/main.py", "src/__main__.py"]:
            if Path(entry).exists():
                couplings.append({
                    "sources": [entry],
                    "docs": ["README.md"],
                    "description": "Main entry point",
                })
                break

    # Pattern: CLAUDE.md subdirectories
    for claude_md in Path(".").rglob("**/CLAUDE.md"):
        if claude_md.parent != Path("."):
            parent = str(claude_md.parent)
            couplings.append({
                "sources": [f"{parent}/**/*.py"],
                "docs": [str(claude_md)],
                "description": f"Module documentation: {parent}",
            })

    return couplings


def suggest_adrs() -> list[dict[str, Any]]:
    """Suggest ADRs based on detected patterns."""
    suggestions: list[dict[str, Any]] = []

    patterns = [
        ("requirements.txt", "Dependency management approach", "medium"),
        ("pyproject.toml", "Python project configuration", "medium"),
        ("Dockerfile", "Containerization strategy", "medium"),
        ("docker-compose.yml", "Service orchestration", "medium"),
        ("docker-compose.yaml", "Service orchestration", "medium"),
        (".github/workflows", "CI/CD approach", "high"),
        ("alembic.ini", "Database migration strategy", "medium"),
        ("pytest.ini", "Testing strategy", "low"),
        ("pyproject.toml", "Testing strategy", "low"),
        (".pre-commit-config.yaml", "Code quality enforcement", "low"),
        ("Makefile", "Build automation", "low"),
        (".env.example", "Configuration management", "medium"),
        ("config/", "Configuration structure", "medium"),
    ]

    seen_titles: set[str] = set()
    for pattern, description, priority in patterns:
        if Path(pattern).exists() and description not in seen_titles:
            suggestions.append({
                "title": description,
                "detected_from": pattern,
                "priority": priority,
            })
            seen_titles.add(description)

    return suggestions


def detect_patterns() -> list[str]:
    """Detect common architecture patterns in the codebase."""
    patterns: list[str] = []

    # Detect package structure
    if Path("src").is_dir() and Path("tests").is_dir():
        patterns.append("src-tests layout")

    # Detect Django
    if Path("manage.py").exists() and Path("settings.py").exists():
        patterns.append("Django project")

    # Detect FastAPI/Flask
    if any(Path(".").rglob("**/app.py")):
        with open(next(Path(".").rglob("**/app.py"))) as f:
            content = f.read()
            if "FastAPI" in content:
                patterns.append("FastAPI application")
            elif "Flask" in content:
                patterns.append("Flask application")

    # Detect CLI tool
    if Path("cli.py").exists() or Path("src/cli.py").exists():
        patterns.append("CLI application")

    # Detect monorepo
    if Path("packages").is_dir() or Path("apps").is_dir():
        patterns.append("Monorepo structure")

    # Detect existing CLAUDE.md files
    claude_files = list(Path(".").rglob("**/CLAUDE.md"))
    if len(claude_files) > 1:
        patterns.append(f"Multi-level CLAUDE.md ({len(claude_files)} files)")

    return patterns


def init_meta_process(weight: str = "light") -> None:
    """Initialize meta-process files.

    Args:
        weight: Starting weight level (minimal, light, medium, heavy).
    """
    # Create meta-process.yaml
    meta_process = {
        "weight": weight,
        "bootstrap": {
            "date": datetime.now().isoformat(),
            "initial_weight": weight,
        },
        "enforcement": {
            "plan_index_auto_add": True,
            "strict_doc_coupling": weight in ("medium", "heavy"),
            "show_strictness_warning": True,
        },
        "hooks": {
            "protect_main": weight in ("medium", "heavy"),
            "enforce_workflow": weight in ("medium", "heavy"),
            "warn_worktree_cwd": True,
            "session_cleanup": True,
            "inject_governance_context": True,
        },
    }

    if not Path("meta-process.yaml").exists():
        with open("meta-process.yaml", "w") as f:
            yaml.dump(meta_process, f, default_flow_style=False, sort_keys=False)
        print("Created: meta-process.yaml")
    else:
        print("Skipped: meta-process.yaml (already exists)")

    # Create scripts directory if needed
    Path("scripts").mkdir(exist_ok=True)

    # Create starter relationships.yaml
    if not Path("scripts/relationships.yaml").exists():
        couplings = suggest_couplings()
        relationships = {
            "adrs": {},
            "governance": [],
            "couplings": couplings if couplings else [
                {
                    "sources": ["src/**/*.py"],
                    "docs": ["README.md"],
                    "description": "Source code changes may require README updates",
                    "soft": True,
                }
            ],
        }
        with open("scripts/relationships.yaml", "w") as f:
            yaml.dump(relationships, f, default_flow_style=False, sort_keys=False)
        print("Created: scripts/relationships.yaml")
    else:
        print("Skipped: scripts/relationships.yaml (already exists)")

    # Create docs/plans/ if needed
    Path("docs/plans").mkdir(parents=True, exist_ok=True)
    print("Created: docs/plans/")

    # Create docs/adr/ if needed
    Path("docs/adr").mkdir(parents=True, exist_ok=True)
    print("Created: docs/adr/")

    # Create starter CLAUDE.md if not exists
    if not Path("CLAUDE.md").exists():
        create_starter_claude_md()
        print("Created: CLAUDE.md")
    else:
        print("Skipped: CLAUDE.md (already exists)")

    print()
    print(f"Initialized meta-process at weight: {weight}")
    print()
    print("Next steps:")
    print("  1. Review scripts/relationships.yaml - verify suggested couplings")
    print("  2. Create your first ADR in docs/adr/ documenting core architecture")
    print("  3. Run: python scripts/bootstrap_meta_process.py --progress")


def create_starter_claude_md() -> None:
    """Create a starter CLAUDE.md file."""
    content = """# Project Name

> Brief description of what this project does.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

## Project Structure

```
.
├── src/            # Source code
├── tests/          # Test files
├── docs/           # Documentation
│   ├── plans/      # Implementation plans
│   └── adr/        # Architecture Decision Records
├── scripts/        # Utility scripts
└── config/         # Configuration files
```

## Development

```bash
# Run tests
pytest tests/ -v

# Check types
python -m mypy src/ --ignore-missing-imports
```

## Meta-Process

This project uses the meta-process for coordination. See:
- `meta-process.yaml` - Configuration
- `scripts/relationships.yaml` - Doc-code coupling definitions
- `docs/plans/` - Implementation plans

---

*Generated by bootstrap_meta_process.py*
"""
    with open("CLAUDE.md", "w") as f:
        f.write(content)


def calculate_compliance() -> dict[str, Any]:
    """Calculate meta-process compliance score.

    Returns:
        Dict with compliance metrics.
    """
    metrics: dict[str, Any] = {
        "adr_count": 0,
        "coupling_count": 0,
        "plan_count": 0,
        "has_claude_md": Path("CLAUDE.md").exists(),
        "has_meta_process": Path("meta-process.yaml").exists(),
        "has_relationships": Path("scripts/relationships.yaml").exists(),
        "weight": "unknown",
        "score": 0,
    }

    # Count ADRs
    if Path("docs/adr").exists():
        metrics["adr_count"] = len(list(Path("docs/adr").glob("*.md")))

    # Count plans
    if Path("docs/plans").exists():
        metrics["plan_count"] = len([
            f for f in Path("docs/plans").glob("*.md")
            if f.name not in ("CLAUDE.md", "TEMPLATE.md")
        ])

    # Count couplings
    if Path("scripts/relationships.yaml").exists():
        with open("scripts/relationships.yaml") as f:
            data = yaml.safe_load(f) or {}
        metrics["coupling_count"] = len(data.get("couplings", []))

    # Get weight
    if Path("meta-process.yaml").exists():
        with open("meta-process.yaml") as f:
            data = yaml.safe_load(f) or {}
        metrics["weight"] = data.get("weight", "medium")

    # Calculate score (0-100)
    score = 0
    if metrics["has_claude_md"]:
        score += 20
    if metrics["has_meta_process"]:
        score += 20
    if metrics["has_relationships"]:
        score += 10
    if metrics["adr_count"] >= 1:
        score += 15
    if metrics["adr_count"] >= 3:
        score += 10
    if metrics["coupling_count"] >= 3:
        score += 10
    if metrics["coupling_count"] >= 5:
        score += 5
    if metrics["plan_count"] >= 1:
        score += 10

    metrics["score"] = score
    return metrics


def get_recommendations(metrics: dict[str, Any]) -> list[str]:
    """Generate recommendations for next steps.

    Args:
        metrics: Compliance metrics from calculate_compliance().

    Returns:
        List of recommendation strings.
    """
    recs: list[str] = []

    if not metrics["has_claude_md"]:
        recs.append("Create CLAUDE.md with project overview")

    if not metrics["has_meta_process"]:
        recs.append("Run --init to create meta-process.yaml")

    if not metrics["has_relationships"]:
        recs.append("Create scripts/relationships.yaml with doc-code couplings")

    if metrics["adr_count"] == 0:
        recs.append("Create your first ADR documenting a key architectural decision")

    if metrics["coupling_count"] < 3:
        recs.append("Add more doc-code couplings to relationships.yaml")

    if metrics["weight"] == "minimal" and metrics["score"] > 50:
        recs.append("Consider upgrading to 'light' weight")

    if metrics["weight"] == "light" and metrics["score"] > 75:
        recs.append("Consider upgrading to 'medium' weight")

    if metrics["weight"] == "medium" and metrics["score"] > 90:
        recs.append("Consider upgrading to 'heavy' weight for full enforcement")

    if not recs:
        recs.append("Great progress! Keep documenting as you go.")

    return recs


def show_progress() -> None:
    """Show progress toward full meta-process adoption."""
    metrics = calculate_compliance()

    print("=" * 60)
    print("Meta-Process Adoption Progress")
    print("=" * 60)
    print()
    print(f"Current weight: {metrics['weight']}")
    print(f"Compliance score: {metrics['score']}%")
    print()
    print("Components:")
    print(f"  CLAUDE.md:           {'Yes' if metrics['has_claude_md'] else 'No'}")
    print(f"  meta-process.yaml:   {'Yes' if metrics['has_meta_process'] else 'No'}")
    print(f"  relationships.yaml:  {'Yes' if metrics['has_relationships'] else 'No'}")
    print(f"  ADRs documented:     {metrics['adr_count']}")
    print(f"  Couplings defined:   {metrics['coupling_count']}")
    print(f"  Plans created:       {metrics['plan_count']}")
    print()
    print("Recommendations:")
    for rec in get_recommendations(metrics):
        print(f"  - {rec}")
    print()


def show_analysis() -> None:
    """Show repo analysis results."""
    analysis = analyze_repo()

    print("=" * 60)
    print("Repository Analysis")
    print("=" * 60)
    print()
    print("Structure:")
    print(f"  Source files:  {analysis['file_count']}")
    print(f"  Test files:    {analysis['test_count']}")
    print(f"  Doc files:     {analysis['doc_count']}")
    print()
    print("Directories:")
    print(f"  src/:   {'Yes' if analysis['has_src'] else 'No'}")
    print(f"  tests/: {'Yes' if analysis['has_tests'] else 'No'}")
    print(f"  docs/:  {'Yes' if analysis['has_docs'] else 'No'}")
    print()

    if analysis["detected_patterns"]:
        print("Detected patterns:")
        for pattern in analysis["detected_patterns"]:
            print(f"  - {pattern}")
        print()

    if analysis["suggested_couplings"]:
        print(f"Suggested couplings ({len(analysis['suggested_couplings'])}):")
        for coupling in analysis["suggested_couplings"][:5]:
            print(f"  - {coupling['description']}")
            print(f"    {coupling['sources'][0]} -> {coupling['docs'][0]}")
        if len(analysis["suggested_couplings"]) > 5:
            print(f"  ... and {len(analysis['suggested_couplings']) - 5} more")
        print()

    if analysis["suggested_adrs"]:
        print("Suggested ADRs:")
        for adr in analysis["suggested_adrs"]:
            print(f"  - [{adr['priority']}] {adr['title']}")
            print(f"    (detected from: {adr['detected_from']})")
        print()


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Bootstrap meta-process for existing repos"
    )
    parser.add_argument(
        "--analyze",
        action="store_true",
        help="Analyze repo structure and suggest configurations",
    )
    parser.add_argument(
        "--init",
        action="store_true",
        help="Initialize meta-process files",
    )
    parser.add_argument(
        "--weight",
        choices=["minimal", "light", "medium", "heavy"],
        default="light",
        help="Starting weight level (default: light)",
    )
    parser.add_argument(
        "--progress",
        action="store_true",
        help="Show progress toward full adoption",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be created without creating files",
    )

    args = parser.parse_args()

    if args.analyze:
        show_analysis()
    elif args.init:
        if args.dry_run:
            print("Dry run - would create:")
            print("  - meta-process.yaml")
            print("  - scripts/relationships.yaml")
            print("  - docs/plans/")
            print("  - docs/adr/")
            if not Path("CLAUDE.md").exists():
                print("  - CLAUDE.md")
        else:
            init_meta_process(args.weight)
    elif args.progress:
        show_progress()
    else:
        # Default: show analysis and progress
        show_analysis()
        print()
        show_progress()


if __name__ == "__main__":
    main()
