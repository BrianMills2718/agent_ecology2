#!/usr/bin/env python3
"""Check governance mapping completeness for CI (Plan #289 Phase 3).

Validates:
1. Every ADR has at least one governance mapping (ERROR if missing)
2. Source files have governance (WARNING, tracks coverage)
3. Semantic search index is up to date (WARNING if stale)

Exit codes:
  0 - All checks pass
  1 - Critical errors (unmapped ADRs in strict mode)

Usage:
    python scripts/check_governance_completeness.py           # Report mode
    python scripts/check_governance_completeness.py --strict  # CI mode (fails on errors)
    python scripts/check_governance_completeness.py --suggest # Show what to add
"""

import argparse
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

# ADRs that are intentionally unmapped (meta-process, deferred, etc.)
EXEMPT_ADRS = {
    5,   # ADR-0005: Unified Documentation Graph (meta-process, not code)
    6,   # ADR-0006: Minimal External Dependencies (design principle, not specific code)
    18,  # ADR-0018: Bootstrap Phase and Eris (historical context)
    22,  # ADR-0022: Research System Trust Model (not yet implemented)
    25,  # ADR-0025: Deferred Tokenized Rights (explicitly deferred)
}

# Plan #292: Critical files that MUST have governance mappings
# These are core kernel files - errors if missing governance in strict mode
CRITICAL_FILES = {
    # World module - kernel core
    "src/world/world.py",
    "src/world/artifacts.py",
    "src/world/ledger.py",
    "src/world/contracts.py",
    "src/world/executor.py",
    "src/world/action_executor.py",
    "src/world/permission_checker.py",
    "src/world/kernel_interface.py",
    "src/world/resource_manager.py",
    "src/world/logger.py",
    # Agents module - agent core
    "src/agents/agent.py",
    "src/agents/loader.py",
    "src/agents/workflow.py",
    "src/agents/memory.py",
    # Simulation module - runner core
    "src/simulation/runner.py",
}


def load_relationships() -> dict:
    """Load relationships.yaml."""
    rel_path = REPO_ROOT / "scripts" / "relationships.yaml"
    with open(rel_path) as f:
        return yaml.safe_load(f)


def get_all_adrs() -> dict[int, Path]:
    """Get all ADR files mapped by number."""
    adr_dir = REPO_ROOT / "docs" / "adr"
    adrs = {}
    for f in adr_dir.glob("*.md"):
        if f.name in ("CLAUDE.md", "README.md", "TEMPLATE.md"):
            continue
        # Parse number from filename like 0016-created-by-not-owner.md
        parts = f.stem.split("-")
        if parts and parts[0].isdigit():
            adrs[int(parts[0])] = f
    return adrs


def get_all_src_files() -> set[str]:
    """Get all Python source files as relative paths."""
    src_dir = REPO_ROOT / "src"
    files = set()
    for f in src_dir.rglob("*.py"):
        files.add(str(f.relative_to(REPO_ROOT)))
    return files


def check_adr_coverage(relationships: dict, all_adrs: dict[int, Path]) -> tuple[set[int], set[int]]:
    """Check which ADRs have governance mappings.

    Returns (mapped_adrs, unmapped_adrs).
    """
    governance = relationships.get("governance", [])

    mapped_adrs: set[int] = set()
    for entry in governance:
        for adr_num in entry.get("adrs", []):
            mapped_adrs.add(adr_num)

    all_adr_nums = set(all_adrs.keys())
    unmapped = all_adr_nums - mapped_adrs - EXEMPT_ADRS

    return mapped_adrs, unmapped


def check_src_coverage(relationships: dict, all_src: set[str]) -> tuple[set[str], set[str]]:
    """Check which source files have governance mappings.

    Returns (mapped_files, unmapped_files).
    """
    governance = relationships.get("governance", [])

    mapped_files: set[str] = set()
    for entry in governance:
        source = entry.get("source", "")
        if source:
            mapped_files.add(source)

    unmapped = all_src - mapped_files
    return mapped_files, unmapped


def check_critical_files(mapped_files: set[str]) -> set[str]:
    """Check which critical files are missing governance (Plan #292).

    Returns set of unmapped critical files.
    """
    return CRITICAL_FILES - mapped_files


def check_index_freshness() -> tuple[bool, str]:
    """Check if semantic search index exists and is reasonably fresh.

    Returns (is_ok, message).
    """
    index_path = REPO_ROOT / "data" / "doc_index.json"

    if not index_path.exists():
        return False, "Index missing. Run: python scripts/build_doc_index.py"

    # Check if any doc source is newer than index
    index_mtime = index_path.stat().st_mtime

    doc_dirs = [
        REPO_ROOT / "docs" / "adr",
        REPO_ROOT / "docs" / "architecture" / "current",
    ]
    doc_files = [
        REPO_ROOT / "docs" / "GLOSSARY.md",
        REPO_ROOT / "docs" / "ONTOLOGY.yaml",
    ]

    stale_sources = []
    for doc_dir in doc_dirs:
        if doc_dir.exists():
            for f in doc_dir.glob("*.md"):
                if f.stat().st_mtime > index_mtime:
                    stale_sources.append(str(f.relative_to(REPO_ROOT)))

    for doc_file in doc_files:
        if doc_file.exists() and doc_file.stat().st_mtime > index_mtime:
            stale_sources.append(str(doc_file.relative_to(REPO_ROOT)))

    if stale_sources:
        return False, f"Index stale. Changed: {', '.join(stale_sources[:3])}{'...' if len(stale_sources) > 3 else ''}"

    return True, "Index up to date"


def get_adr_title(adr_path: Path) -> str:
    """Extract title from ADR file."""
    with open(adr_path) as f:
        for line in f:
            if line.startswith("# "):
                return line[2:].strip()
    return adr_path.stem


def suggest_mappings(unmapped_adrs: set[int], all_adrs: dict[int, Path]) -> None:
    """Suggest governance mappings for unmapped ADRs."""
    print("\n## Suggested Mappings")
    print("Add to scripts/relationships.yaml governance section:\n")

    for adr_num in sorted(unmapped_adrs):
        adr_path = all_adrs.get(adr_num)
        if adr_path:
            title = get_adr_title(adr_path)
            print(f"  # ADR-{adr_num:04d}: {title}")
            print(f"  - source: src/???  # TODO: identify relevant file")
            print(f"    adrs: [{adr_num}]")
            print(f"    context: |")
            print(f"      TODO: Add context about how this ADR applies")
            print()


def main() -> int:
    parser = argparse.ArgumentParser(description="Check governance completeness")
    parser.add_argument("--strict", action="store_true",
                        help="Fail on unmapped ADRs (for CI)")
    parser.add_argument("--suggest", action="store_true",
                        help="Show suggested mappings for unmapped ADRs")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="Only show errors and warnings")
    args = parser.parse_args()

    relationships = load_relationships()
    all_adrs = get_all_adrs()
    all_src = get_all_src_files()

    errors = []
    warnings = []

    # Check ADR coverage
    mapped_adrs, unmapped_adrs = check_adr_coverage(relationships, all_adrs)
    adr_coverage = len(mapped_adrs) / len(all_adrs) * 100 if all_adrs else 0

    if unmapped_adrs:
        for adr_num in sorted(unmapped_adrs):
            adr_path = all_adrs.get(adr_num)
            title = get_adr_title(adr_path) if adr_path else f"ADR-{adr_num:04d}"
            errors.append(f"ADR-{adr_num:04d} has no governance mapping: {title}")

    # Check source file coverage
    mapped_src, unmapped_src = check_src_coverage(relationships, all_src)
    src_coverage = len(mapped_src) / len(all_src) * 100 if all_src else 0

    if src_coverage < 20:
        warnings.append(f"Low source file governance coverage: {src_coverage:.0f}%")

    # Check critical files (Plan #292)
    unmapped_critical = check_critical_files(mapped_src)
    if unmapped_critical:
        for f in sorted(unmapped_critical):
            errors.append(f"Critical file has no governance mapping: {f}")

    # Check index freshness
    index_ok, index_msg = check_index_freshness()
    if not index_ok:
        warnings.append(f"Semantic search index: {index_msg}")

    # Output
    if not args.quiet:
        print("=" * 60)
        print("GOVERNANCE COMPLETENESS CHECK (Plan #289, #292)")
        print("=" * 60)

        print(f"\n## ADR Coverage: {len(mapped_adrs)}/{len(all_adrs)} ({adr_coverage:.0f}%)")
        if EXEMPT_ADRS:
            print(f"   (Exempt: {', '.join(f'ADR-{n:04d}' for n in sorted(EXEMPT_ADRS))})")

        print(f"\n## Source Coverage: {len(mapped_src)}/{len(all_src)} ({src_coverage:.0f}%)")

        # Critical files coverage (Plan #292)
        critical_mapped = len(CRITICAL_FILES) - len(unmapped_critical)
        print(f"\n## Critical Files: {critical_mapped}/{len(CRITICAL_FILES)} ({critical_mapped / len(CRITICAL_FILES) * 100:.0f}%)")

        print(f"\n## Semantic Index: {index_msg}")

    if errors:
        print("\n" + "=" * 60)
        print("ERRORS (must fix):")
        print("=" * 60)
        for e in errors:
            print(f"  ❌ {e}")

    if warnings:
        print("\n" + "=" * 60)
        print("WARNINGS:")
        print("=" * 60)
        for w in warnings:
            print(f"  ⚠️  {w}")

    if args.suggest and unmapped_adrs:
        suggest_mappings(unmapped_adrs, all_adrs)

    # Summary
    if not args.quiet:
        print("\n" + "=" * 60)
        if not errors and not warnings:
            print("✅ All governance checks passed")
        elif errors:
            print(f"❌ {len(errors)} error(s), {len(warnings)} warning(s)")
        else:
            print(f"⚠️  {len(warnings)} warning(s)")
        print("=" * 60)

    # Exit code
    if args.strict and errors:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
