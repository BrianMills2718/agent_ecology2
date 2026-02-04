#!/usr/bin/env python3
"""Audit governance mappings for completeness (Plan #289).

Shows:
- ADRs with no governance mappings
- Source files with no governance
- Coverage statistics
"""

import argparse
import sys
from pathlib import Path

import yaml


def load_relationships() -> dict:
    """Load the relationships.yaml file."""
    repo_root = Path(__file__).parent.parent
    rel_path = repo_root / "scripts" / "relationships.yaml"
    with open(rel_path) as f:
        return yaml.safe_load(f)


def get_all_adrs() -> list[Path]:
    """Get all ADR files (excluding meta files)."""
    repo_root = Path(__file__).parent.parent
    adr_dir = repo_root / "docs" / "adr"
    adrs = []
    for f in sorted(adr_dir.glob("*.md")):
        # Skip meta files
        if f.name in ("CLAUDE.md", "README.md", "TEMPLATE.md"):
            continue
        adrs.append(f)
    return adrs


def get_all_src_files() -> list[Path]:
    """Get all Python source files."""
    repo_root = Path(__file__).parent.parent
    src_dir = repo_root / "src"
    return sorted(src_dir.rglob("*.py"))


def parse_adr_number(adr_path: Path) -> int | None:
    """Extract ADR number from filename like 0016-created-by-not-owner.md."""
    name = adr_path.stem  # e.g., "0016-created-by-not-owner"
    parts = name.split("-")
    if parts and parts[0].isdigit():
        return int(parts[0])
    return None


def audit_governance(relationships: dict) -> dict:
    """Audit governance mappings."""
    governance = relationships.get("governance", [])

    # Build set of mapped ADRs and files
    mapped_adrs: set[int] = set()
    mapped_files: set[str] = set()

    for entry in governance:
        source = entry.get("source", "")
        adrs = entry.get("adrs", [])
        mapped_files.add(source)
        mapped_adrs.update(adrs)

    # Get all ADRs
    all_adrs = get_all_adrs()
    all_adr_numbers = {parse_adr_number(a) for a in all_adrs if parse_adr_number(a) is not None}

    # Get all source files
    all_src = get_all_src_files()
    repo_root = Path(__file__).parent.parent
    all_src_relative = {str(f.relative_to(repo_root)) for f in all_src}

    # Find unmapped
    unmapped_adrs = all_adr_numbers - mapped_adrs
    unmapped_files = all_src_relative - mapped_files

    return {
        "total_adrs": len(all_adr_numbers),
        "mapped_adrs": len(mapped_adrs),
        "unmapped_adrs": sorted(unmapped_adrs),
        "total_src_files": len(all_src_relative),
        "mapped_src_files": len(mapped_files),
        "unmapped_src_files": sorted(unmapped_files),
        "all_adrs": all_adrs,
    }


def get_adr_title(adr_path: Path) -> str:
    """Extract title from ADR file."""
    with open(adr_path) as f:
        for line in f:
            if line.startswith("# "):
                return line[2:].strip()
    return adr_path.stem


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit governance mappings")
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all unmapped files")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    relationships = load_relationships()
    audit = audit_governance(relationships)

    if args.json:
        import json
        print(json.dumps(audit, indent=2, default=str))
        return 0

    print("=" * 70)
    print("GOVERNANCE MAPPING AUDIT (Plan #289)")
    print("=" * 70)

    # ADR coverage
    adr_coverage = audit["mapped_adrs"] / audit["total_adrs"] * 100 if audit["total_adrs"] > 0 else 0
    print(f"\n## ADR Coverage: {audit['mapped_adrs']}/{audit['total_adrs']} ({adr_coverage:.0f}%)")

    if audit["unmapped_adrs"]:
        print(f"\n### ADRs with NO governance mappings ({len(audit['unmapped_adrs'])}):")
        for adr_num in audit["unmapped_adrs"]:
            # Find the ADR file
            for adr_path in audit["all_adrs"]:
                if parse_adr_number(adr_path) == adr_num:
                    title = get_adr_title(adr_path)
                    print(f"   ADR-{adr_num:04d}: {title}")
                    break
    else:
        print("\n   All ADRs have governance mappings!")

    # Source file coverage
    src_coverage = audit["mapped_src_files"] / audit["total_src_files"] * 100 if audit["total_src_files"] > 0 else 0
    print(f"\n## Source File Coverage: {audit['mapped_src_files']}/{audit['total_src_files']} ({src_coverage:.0f}%)")

    if audit["unmapped_src_files"] and args.verbose:
        print(f"\n### Source files with NO governance ({len(audit['unmapped_src_files'])}):")
        for f in audit["unmapped_src_files"][:20]:  # Limit to first 20
            print(f"   {f}")
        if len(audit["unmapped_src_files"]) > 20:
            print(f"   ... and {len(audit['unmapped_src_files']) - 20} more")
    elif audit["unmapped_src_files"]:
        print(f"   {len(audit['unmapped_src_files'])} files without governance (use -v to list)")

    print("\n" + "=" * 70)

    # Summary
    if adr_coverage < 50:
        print("STATUS: CRITICAL - Most ADRs have no governance mappings")
        return 1
    elif adr_coverage < 80:
        print("STATUS: WARNING - Many ADRs missing governance mappings")
        return 0
    else:
        print("STATUS: OK - Good governance coverage")
        return 0


if __name__ == "__main__":
    sys.exit(main())
