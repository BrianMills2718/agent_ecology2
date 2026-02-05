#!/usr/bin/env python3
"""Check that source files have context links in relationships.yaml (Plan #294).

This script validates that:
1. All src/ files have entries in file_context or are covered by directory_defaults
2. All context links (PRD, domain model) resolve to existing files/sections

Usage:
    python scripts/check_file_context.py              # Check all src/ files
    python scripts/check_file_context.py --strict     # Exit 1 if issues found
    python scripts/check_file_context.py --staged     # Only check staged files
    python scripts/check_file_context.py --validate   # Also validate links resolve
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

import yaml


def get_repo_root() -> Path:
    """Get repository root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


REPO_ROOT = get_repo_root()


def load_relationships() -> dict:
    """Load relationships.yaml."""
    rel_path = REPO_ROOT / "scripts" / "relationships.yaml"
    if not rel_path.exists():
        return {}
    return yaml.safe_load(rel_path.read_text())


def get_staged_files() -> list[str]:
    """Get list of staged Python files in src/."""
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACM"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    files = []
    for f in result.stdout.strip().split("\n"):
        if f.startswith("src/") and f.endswith(".py"):
            files.append(f)
    return files


def get_all_src_files() -> list[str]:
    """Get all Python files in src/."""
    files = []
    for path in (REPO_ROOT / "src").rglob("*.py"):
        rel_path = str(path.relative_to(REPO_ROOT))
        files.append(rel_path)
    return sorted(files)


def is_exempt(file_path: str, relationships: dict) -> bool:
    """Check if file is exempt from context requirement."""
    exempt = relationships.get("file_context_exempt", [])
    for pattern in exempt:
        # Simple glob matching
        regex = pattern.replace("**", ".*").replace("*", "[^/]*")
        if re.match(regex, file_path):
            return True
    return False


def has_context(file_path: str, relationships: dict) -> tuple[bool, str]:
    """Check if file has context links. Returns (has_context, source)."""
    file_context = relationships.get("file_context", {})
    directory_defaults = relationships.get("directory_defaults", {})

    # Check explicit file_context
    if file_path in file_context:
        return True, "file_context"

    # Check directory_defaults
    for dir_pattern in directory_defaults:
        if file_path.startswith(dir_pattern.rstrip("/")):
            return True, f"directory_default:{dir_pattern}"

    return False, ""


def validate_prd_link(ref: str) -> tuple[bool, str]:
    """Validate a PRD reference exists."""
    if "#" in ref:
        domain, section = ref.split("#", 1)
    else:
        domain = ref
        section = None

    prd_path = REPO_ROOT / "docs" / "prd" / f"{domain}.md"
    if not prd_path.exists():
        return False, f"PRD file not found: docs/prd/{domain}.md"

    if section:
        content = prd_path.read_text()
        # Look for section header
        pattern = rf"^###?\s+{re.escape(section)}\s*$"
        if not re.search(pattern, content, re.MULTILINE | re.IGNORECASE):
            return False, f"Section '{section}' not found in docs/prd/{domain}.md"

    return True, ""


def validate_dm_link(ref: str) -> tuple[bool, str]:
    """Validate a domain model reference exists."""
    if "#" in ref:
        domain, concept = ref.split("#", 1)
    else:
        domain = ref
        concept = None

    dm_path = REPO_ROOT / "docs" / "domain_model" / f"{domain}.yaml"
    if not dm_path.exists():
        return False, f"Domain model not found: docs/domain_model/{domain}.yaml"

    if concept:
        try:
            dm = yaml.safe_load(dm_path.read_text())
            concepts = dm.get("concepts", {})
            if concept not in concepts:
                return False, f"Concept '{concept}' not found in docs/domain_model/{domain}.yaml"
        except Exception as e:
            return False, f"Failed to parse domain model: {e}"

    return True, ""


def validate_links(relationships: dict) -> list[str]:
    """Validate all context links resolve."""
    errors = []

    file_context = relationships.get("file_context", {})
    for file_path, ctx in file_context.items():
        for ref in ctx.get("prd", []):
            valid, msg = validate_prd_link(ref)
            if not valid:
                errors.append(f"{file_path}: PRD link error - {msg}")

        for ref in ctx.get("domain_model", []):
            valid, msg = validate_dm_link(ref)
            if not valid:
                errors.append(f"{file_path}: Domain model link error - {msg}")

    return errors


def main():
    parser = argparse.ArgumentParser(description="Check file context links")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if issues found")
    parser.add_argument("--staged", action="store_true", help="Only check staged files")
    parser.add_argument("--validate", action="store_true", help="Also validate links resolve")
    args = parser.parse_args()

    relationships = load_relationships()

    if args.staged:
        files = get_staged_files()
    else:
        files = get_all_src_files()

    missing = []
    covered = []

    for f in files:
        if is_exempt(f, relationships):
            continue

        has_ctx, source = has_context(f, relationships)
        if has_ctx:
            covered.append((f, source))
        else:
            missing.append(f)

    # Report
    if missing:
        print("=" * 60)
        print("FILES WITHOUT CONTEXT LINKS")
        print("=" * 60)
        print()
        for f in missing:
            print(f"  {f}")
        print()
        print(f"Total: {len(missing)} files without context")
        print()
        print("Add to scripts/relationships.yaml file_context or directory_defaults")
        print()

    # Validate links if requested
    link_errors = []
    if args.validate:
        link_errors = validate_links(relationships)
        if link_errors:
            print("=" * 60)
            print("LINK VALIDATION ERRORS")
            print("=" * 60)
            print()
            for err in link_errors:
                print(f"  {err}")
            print()

    # Summary
    print("-" * 60)
    print(f"Checked: {len(files)} files")
    print(f"Covered: {len(covered)}")
    print(f"Missing: {len(missing)}")
    if args.validate:
        print(f"Link errors: {len(link_errors)}")

    if args.strict and (missing or link_errors):
        sys.exit(1)


if __name__ == "__main__":
    main()
