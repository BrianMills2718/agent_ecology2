#!/usr/bin/env python3
"""Validate Code Map in CLAUDE.md files.

Checks that:
1. Files/directories referenced in Code Map tables actually exist
2. Optionally reports src files not documented in any Code Map

Usage:
    # Check all CLAUDE.md files
    python scripts/validate_code_map.py

    # Check specific file
    python scripts/validate_code_map.py --file CLAUDE.md

    # Also report undocumented files
    python scripts/validate_code_map.py --report-undocumented

    # CI mode (exit 1 if stale entries)
    python scripts/validate_code_map.py --strict
"""

import argparse
import re
import sys
from pathlib import Path


def find_claude_md_files(root: Path) -> list[Path]:
    """Find all CLAUDE.md files in the project."""
    return list(root.rglob("CLAUDE.md"))


def parse_code_map_table(content: str) -> list[dict[str, str]]:
    """Parse Code Map table from CLAUDE.md content.

    Expected format:
    ## Code Map
    | Domain | Location | Purpose |
    |--------|----------|---------|
    | Core | src/core/ | Core logic |

    or

    ## Code Map (src/)
    | File | Key Elements | Purpose |
    |------|--------------|---------|
    | world/ledger.py | Ledger class | Balance management |

    Returns list of dicts with parsed table data.
    """
    entries = []

    # Find Code Map sections (may have suffix like "Code Map (src/)")
    pattern = r"##\s*Code\s*Map[^\n]*\n(.*?)(?=\n##|\n---|\Z)"
    matches = re.finditer(pattern, content, re.IGNORECASE | re.DOTALL)

    for match in matches:
        section = match.group(1)

        # Find table rows (skip header and separator)
        lines = section.strip().split("\n")

        # Skip until we find a table
        in_table = False
        header_cols = []

        for line in lines:
            line = line.strip()

            if not line.startswith("|"):
                in_table = False
                continue

            # Parse table row
            cells = [c.strip() for c in line.split("|")[1:-1]]

            if not cells:
                continue

            # Check if this is separator row (all dashes)
            if all(re.match(r"^[-:]+$", c) for c in cells):
                in_table = True
                continue

            if not in_table:
                # This is header row
                header_cols = [c.lower() for c in cells]
                continue

            # This is data row
            if len(cells) >= 2:
                entry = {}
                for i, col in enumerate(header_cols):
                    if i < len(cells):
                        entry[col] = cells[i]

                # Extract location/file path
                location = entry.get("location") or entry.get("file") or entry.get("path")
                if location:
                    entry["_path"] = location.strip("`")
                    entries.append(entry)

    return entries


def validate_path(path: str, root: Path, base_dir: Path | None = None) -> tuple[bool, str]:
    """Check if a path exists.

    Args:
        path: Path from Code Map (may be relative)
        root: Project root directory
        base_dir: Base directory for relative paths (e.g., src/ for src/CLAUDE.md)

    Returns:
        (exists, resolved_path)
    """
    # Try various interpretations
    candidates = [
        root / path,
        root / path.lstrip("/"),
    ]

    if base_dir:
        candidates.insert(0, base_dir / path)

    for candidate in candidates:
        if candidate.exists():
            return True, str(candidate)

    return False, path


def get_documented_paths(claude_files: list[Path], root: Path) -> set[str]:
    """Get all paths documented in Code Maps."""
    documented = set()

    for claude_file in claude_files:
        content = claude_file.read_text()
        entries = parse_code_map_table(content)

        # Determine base directory for this CLAUDE.md
        base_dir = claude_file.parent
        if base_dir == root:
            base_dir = None

        for entry in entries:
            path = entry.get("_path", "")
            if path:
                # Resolve to absolute path
                exists, resolved = validate_path(path, root, base_dir)
                if exists:
                    # Normalize to relative path from root
                    try:
                        rel_path = str(Path(resolved).relative_to(root))
                        documented.add(rel_path)
                        # Also add the directory if it's a file
                        if Path(resolved).is_file():
                            documented.add(str(Path(rel_path).parent))
                    except ValueError:
                        documented.add(resolved)

    return documented


def find_undocumented_src_files(root: Path, documented: set[str]) -> list[str]:
    """Find src files not in any Code Map."""
    undocumented = []
    src_dir = root / "src"

    if not src_dir.exists():
        return undocumented

    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith("__"):
            continue

        rel_path = str(py_file.relative_to(root))

        # Check if file or any parent directory is documented
        is_documented = False
        path_parts = Path(rel_path).parts

        for i in range(len(path_parts)):
            check_path = str(Path(*path_parts[: i + 1]))
            if check_path in documented:
                is_documented = True
                break

        if not is_documented:
            undocumented.append(rel_path)

    return sorted(undocumented)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Code Map in CLAUDE.md files",
    )
    parser.add_argument(
        "--file", "-f",
        type=str,
        help="Check specific CLAUDE.md file"
    )
    parser.add_argument(
        "--report-undocumented", "-u",
        action="store_true",
        help="Also report src files not in any Code Map"
    )
    parser.add_argument(
        "--strict", "-s",
        action="store_true",
        help="CI mode: exit 1 if any stale entries found"
    )

    args = parser.parse_args()

    # Find project root
    root = Path.cwd()

    # Find CLAUDE.md files to check
    if args.file:
        claude_files = [Path(args.file)]
    else:
        claude_files = find_claude_md_files(root)

    if not claude_files:
        print("No CLAUDE.md files found")
        return 0

    # Track issues
    stale_entries = []
    total_entries = 0

    # Check each file
    for claude_file in claude_files:
        if not claude_file.exists():
            print(f"Warning: {claude_file} not found")
            continue

        content = claude_file.read_text()
        entries = parse_code_map_table(content)

        if not entries:
            continue

        # Determine base directory
        base_dir = claude_file.parent
        if base_dir == root:
            base_dir = None

        print(f"\n{claude_file}:")

        for entry in entries:
            total_entries += 1
            path = entry.get("_path", "")

            if not path:
                continue

            exists, resolved = validate_path(path, root, base_dir)

            if exists:
                print(f"  ✓ {path}")
            else:
                print(f"  ✗ {path} (NOT FOUND)")
                stale_entries.append({
                    "file": str(claude_file),
                    "path": path,
                })

    # Summary
    print(f"\n{'=' * 50}")
    print(f"Total entries checked: {total_entries}")
    print(f"Stale entries: {len(stale_entries)}")

    if stale_entries:
        print("\nStale entries to fix:")
        for entry in stale_entries:
            print(f"  {entry['file']}: {entry['path']}")

    # Check undocumented files
    if args.report_undocumented:
        documented = get_documented_paths(claude_files, root)
        undocumented = find_undocumented_src_files(root, documented)

        if undocumented:
            print(f"\nUndocumented src files ({len(undocumented)}):")
            for f in undocumented[:20]:  # Limit output
                print(f"  - {f}")
            if len(undocumented) > 20:
                print(f"  ... and {len(undocumented) - 20} more")

    # Return code
    if args.strict and stale_entries:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
