#!/usr/bin/env python3
"""Validate internal consistency of relationships.yaml.

Checks that all references resolve: governance source files exist,
ADR numbers are registered, coupling patterns match real files, etc.

Usage:
    python scripts/validate_relationships.py          # Full validation
    python scripts/validate_relationships.py --fix    # Show suggested fixes

Exit codes:
    0 - All checks pass
    1 - Validation errors found
"""

import argparse
import sys
from pathlib import Path

import yaml


def find_repo_root() -> Path:
    """Find the repository root by looking for .git directory."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / ".git").exists():
            return current
        current = current.parent
    return Path.cwd()


def load_relationships(repo_root: Path) -> dict:  # type: ignore[type-arg]
    """Load relationships.yaml."""
    rel_path = repo_root / "scripts" / "relationships.yaml"
    if not rel_path.exists():
        print(f"ERROR: {rel_path} not found")
        sys.exit(2)
    with open(rel_path) as f:
        return yaml.safe_load(f) or {}


def check_governance_sources(
    relationships: dict, repo_root: Path  # type: ignore[type-arg]
) -> list[str]:
    """Check that all governance source files exist."""
    errors = []
    for entry in relationships.get("governance", []):
        source = entry.get("source", "")
        if not (repo_root / source).exists():
            adrs = entry.get("adrs", [])
            errors.append(
                f"  governance: {source} does not exist (ADRs: {adrs})"
            )
    return errors


def check_adr_references(
    relationships: dict,  # type: ignore[type-arg]
) -> list[str]:
    """Check that all ADR numbers in governance exist in adrs dict."""
    errors = []
    adrs_dict = relationships.get("adrs", {})
    seen: set[tuple[str, int]] = set()
    for entry in relationships.get("governance", []):
        source = entry.get("source", "")
        for adr_num in entry.get("adrs", []):
            if adr_num not in adrs_dict and (source, adr_num) not in seen:
                errors.append(
                    f"  governance: {source} references ADR-{adr_num:04d} "
                    f"which is not in adrs dict"
                )
                seen.add((source, adr_num))
    return errors


def check_adr_files(
    relationships: dict, repo_root: Path  # type: ignore[type-arg]
) -> list[str]:
    """Check that all ADR files on disk are registered in adrs dict."""
    errors = []
    adrs_dict = relationships.get("adrs", {})
    registered_files = {v.get("file", "") for v in adrs_dict.values()}

    adr_dir = repo_root / "docs" / "adr"
    if not adr_dir.exists():
        return errors

    for adr_file in sorted(adr_dir.glob("*.md")):
        if adr_file.name in ("README.md", "CLAUDE.md"):
            continue
        if adr_file.name not in registered_files:
            parts = adr_file.stem.split("-", 1)
            if parts[0].isdigit():
                num = int(parts[0])
                errors.append(
                    f"  adrs: {adr_file.name} (ADR-{num:04d}) exists on "
                    f"disk but not registered in adrs dict"
                )
    return errors


def check_governance_coverage(
    relationships: dict, repo_root: Path  # type: ignore[type-arg]
) -> list[str]:
    """Check that all source .py files have governance entries."""
    warnings = []
    governed_sources = {
        e.get("source", "") for e in relationships.get("governance", [])
    }

    src_dir = repo_root / "src"
    if not src_dir.exists():
        return warnings

    for py_file in sorted(src_dir.rglob("*.py")):
        if py_file.name == "__init__.py":
            continue
        rel_path = str(py_file.relative_to(repo_root))
        if rel_path not in governed_sources:
            warnings.append(
                f"  coverage: {rel_path} has no governance entry"
            )
    return warnings


def check_coupling_sources(
    relationships: dict, repo_root: Path  # type: ignore[type-arg]
) -> list[str]:
    """Check that coupling source patterns match at least one real file."""
    warnings = []
    for coupling in relationships.get("couplings", []):
        for source_pattern in coupling.get("sources", []):
            if "*" in source_pattern or "?" in source_pattern:
                matches = list(repo_root.glob(source_pattern))
                if not matches:
                    warnings.append(
                        f"  couplings: pattern '{source_pattern}' matches no files"
                    )
            else:
                if not (repo_root / source_pattern).exists():
                    warnings.append(
                        f"  couplings: source '{source_pattern}' does not exist"
                    )
    return warnings


def check_coupling_docs(
    relationships: dict, repo_root: Path  # type: ignore[type-arg]
) -> list[str]:
    """Check that coupling doc targets exist."""
    warnings = []
    for coupling in relationships.get("couplings", []):
        for doc in coupling.get("docs", []):
            if not (repo_root / doc).exists():
                warnings.append(
                    f"  couplings: doc '{doc}' does not exist"
                )
    return warnings


def check_file_context_sources(
    relationships: dict, repo_root: Path  # type: ignore[type-arg]
) -> list[str]:
    """Check that file_context entries reference existing files."""
    warnings = []
    for file_path in relationships.get("file_context", {}):
        if not (repo_root / file_path).exists():
            warnings.append(
                f"  file_context: {file_path} does not exist"
            )
    return warnings


def check_duplicate_governance(
    relationships: dict,  # type: ignore[type-arg]
) -> list[str]:
    """Check for duplicate governance entries (same source file)."""
    errors = []
    seen: dict[str, int] = {}
    for i, entry in enumerate(relationships.get("governance", [])):
        source = entry.get("source", "")
        if source in seen:
            errors.append(
                f"  governance: {source} has duplicate entries "
                f"(indices {seen[source]} and {i})"
            )
        else:
            seen[source] = i
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate relationships.yaml internal consistency"
    )
    parser.add_argument(
        "--fix", action="store_true",
        help="Show suggested fixes for each error"
    )
    args = parser.parse_args()

    repo_root = find_repo_root()
    relationships = load_relationships(repo_root)

    all_errors: list[str] = []
    all_warnings: list[str] = []

    print("Checking governance source files...")
    errors = check_governance_sources(relationships, repo_root)
    if errors:
        print(f"  FAIL: {len(errors)} stale governance entries")
        all_errors.extend(errors)
    else:
        print("  OK")

    print("Checking ADR references...")
    errors = check_adr_references(relationships)
    if errors:
        print(f"  FAIL: {len(errors)} unregistered ADR references")
        all_errors.extend(errors)
    else:
        print("  OK")

    print("Checking for duplicate governance entries...")
    errors = check_duplicate_governance(relationships)
    if errors:
        print(f"  FAIL: {len(errors)} duplicates")
        all_errors.extend(errors)
    else:
        print("  OK")

    print("Checking coupling source patterns...")
    errors = check_coupling_sources(relationships, repo_root)
    if errors:
        print(f"  FAIL: {len(errors)} broken coupling sources")
        all_errors.extend(errors)
    else:
        print("  OK")

    print("Checking coupling doc targets...")
    errors = check_coupling_docs(relationships, repo_root)
    if errors:
        print(f"  FAIL: {len(errors)} broken coupling docs")
        all_errors.extend(errors)
    else:
        print("  OK")

    print("Checking file_context entries...")
    errors = check_file_context_sources(relationships, repo_root)
    if errors:
        print(f"  FAIL: {len(errors)} broken file_context entries")
        all_errors.extend(errors)
    else:
        print("  OK")

    # Advisory checks (warnings only)
    print("Checking ADR file registration...")
    warnings = check_adr_files(relationships, repo_root)
    if warnings:
        print(f"  WARN: {len(warnings)} unregistered ADR files")
        all_warnings.extend(warnings)
    else:
        print("  OK")

    print("Checking governance coverage...")
    warnings = check_governance_coverage(relationships, repo_root)
    if warnings:
        print(f"  WARN: {len(warnings)} source files without governance")
        all_warnings.extend(warnings)
    else:
        print("  OK")

    # Summary
    print()
    if all_errors:
        print(f"ERRORS ({len(all_errors)}):")
        for e in all_errors:
            print(e)
        print()

    if all_warnings:
        print(f"WARNINGS ({len(all_warnings)}):")
        for w in all_warnings:
            print(w)
        print()

    if all_errors:
        print(f"FAILED: {len(all_errors)} errors, {len(all_warnings)} warnings")
        return 1
    elif all_warnings:
        print(f"PASSED with {len(all_warnings)} warnings")
        return 0
    else:
        print("PASSED: all checks clean")
        return 0


if __name__ == "__main__":
    sys.exit(main())
