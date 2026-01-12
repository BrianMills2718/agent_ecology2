#!/usr/bin/env python3
"""Check that documentation is updated when coupled source files change.

Usage:
    python scripts/check_doc_coupling.py [--base BASE_REF]

Compares current branch against BASE_REF (default: origin/main) to find
changed files, then checks if coupled docs were also updated.

Exit codes:
    0 - All couplings satisfied (or no coupled changes)
    1 - Missing doc updates (warnings printed)
"""

import argparse
import fnmatch
import subprocess
import sys
from pathlib import Path

import yaml


def get_changed_files(base_ref: str) -> set[str]:
    """Get files changed between base_ref and HEAD."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return set(result.stdout.strip().split("\n")) - {""}
    except subprocess.CalledProcessError:
        # Fallback: compare against HEAD~1 for local testing
        try:
            result = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~1", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )
            return set(result.stdout.strip().split("\n")) - {""}
        except subprocess.CalledProcessError:
            return set()


def load_couplings(config_path: Path) -> list[dict]:
    """Load coupling definitions from YAML."""
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data.get("couplings", [])


def matches_any_pattern(filepath: str, patterns: list[str]) -> bool:
    """Check if filepath matches any glob pattern."""
    for pattern in patterns:
        if fnmatch.fnmatch(filepath, pattern):
            return True
        # Also check without leading path for simple patterns
        if fnmatch.fnmatch(Path(filepath).name, pattern):
            return True
    return False


def check_couplings(changed_files: set[str], couplings: list[dict]) -> list[dict]:
    """Check which couplings have source changes without doc changes.

    Returns list of violated couplings with details.
    """
    violations = []

    for coupling in couplings:
        sources = coupling.get("sources", [])
        docs = coupling.get("docs", [])
        description = coupling.get("description", "")

        # Find which source patterns matched
        matched_sources = []
        for changed in changed_files:
            if matches_any_pattern(changed, sources):
                matched_sources.append(changed)

        if not matched_sources:
            continue  # No source files changed for this coupling

        # Check if any coupled doc was updated
        docs_updated = any(doc in changed_files for doc in docs)

        if not docs_updated:
            violations.append({
                "description": description,
                "changed_sources": matched_sources,
                "expected_docs": docs,
            })

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Check doc-code coupling")
    parser.add_argument(
        "--base",
        default="origin/main",
        help="Base ref to compare against (default: origin/main)",
    )
    parser.add_argument(
        "--config",
        default="scripts/doc_coupling.yaml",
        help="Path to coupling config (default: scripts/doc_coupling.yaml)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code on violations (default: warn only)",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"Config not found: {config_path}")
        return 1

    changed_files = get_changed_files(args.base)
    if not changed_files:
        print("No changed files detected.")
        return 0

    couplings = load_couplings(config_path)
    violations = check_couplings(changed_files, couplings)

    if not violations:
        print("Doc-code coupling check passed.")
        return 0

    # Print violations
    print("=" * 60)
    print("DOC-CODE COUPLING WARNINGS")
    print("=" * 60)
    print()
    print("The following source files changed without corresponding doc updates:")
    print()

    for v in violations:
        print(f"  {v['description']}")
        print(f"    Changed: {', '.join(v['changed_sources'])}")
        print(f"    Expected doc update: {', '.join(v['expected_docs'])}")
        print()

    print("=" * 60)
    print("If the docs are already accurate, update 'Last verified' date.")
    print("=" * 60)

    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
