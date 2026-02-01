#!/usr/bin/env python3
"""CLAUDE.md coverage validation and enforcement.

Ensures every code directory has a CLAUDE.md and that each CLAUDE.md
accurately lists all files in its directory.

Three validation types:
  1. Existence — directories with 2+ tracked files must have CLAUDE.md
  2. Coverage — CLAUDE.md must reference all tracked files in its directory
  3. Phantom — CLAUDE.md must not reference files that don't exist

Usage:
  # Check directories touched by staged files (pre-commit hook)
  python scripts/check_claude_md.py --staged --strict

  # Audit everything
  python scripts/check_claude_md.py --all

  # Show what needs fixing
  python scripts/check_claude_md.py --suggest

  # Print stub table rows for missing files
  python scripts/check_claude_md.py --fix-stub

Exit codes:
  0 - All checks pass (or violations in non-strict mode)
  1 - Violations found (strict mode)
"""

from __future__ import annotations

import argparse
import fnmatch
import re
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Config — loaded from relationships.yaml, with defaults
# ---------------------------------------------------------------------------

DEFAULT_EXEMPT_DIRS: list[str] = [
    "*/static/*",
    "*/static-v2/*",
    "*/api/routes/",
    "dashboard-v2/src/*",
    "dashboard-v2/public/",
    "docs/architecture/gaps/",
    "docs/simulation_learnings/",
    "src/agents/_components/behaviors/",
    "src/agents/_components/evaluators/",
]

DEFAULT_EXEMPT_FILES: list[str] = [
    "CLAUDE.md",
    ".gitignore",
    "*.lock",
    "py.typed",
    "CONTEXT.md",
    "*.svg",
    "*.css",
    "*.html",
]

# Files exempt from coverage in specific directory patterns.
# These are directories where CLAUDE.md describes patterns, not individual files.
COVERAGE_EXEMPT_PATTERNS: dict[str, list[str]] = {
    "tests/unit": ["test_*.py", "__init__.py"],
    "tests/integration": ["test_*.py", "__init__.py"],
    "tests/e2e": ["test_*.py", "__init__.py"],
    "tests": ["test_*.py", "__init__.py", "testing_utils.py"],
    "docs/adr": ["0*-*.md"],
    "meta/acceptance_gates": ["*.yaml"],
    # Root dir: infrastructure files not expected in project structure section
    "": [
        ".claim.yaml", ".dockerignore", ".env.example",
        "Dockerfile", "docker-compose.yml",
        "pyproject.toml", "requirements*.txt",
        "setup.py", "setup.cfg", "Makefile",
        "meta-process.yaml", "README.md",
    ],
}

MIN_FILES_FOR_EXISTENCE = 2

# Regex for things that look like filenames (have extension or trailing slash)
FILENAME_RE = re.compile(
    r"^[\w./-]+\.(py|md|yaml|yml|json|ts|tsx|js|jsx|sh|txt|cfg|toml|ini|csv)$"
    r"|^[\w.-]+/$"  # directory with trailing slash
)


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def get_tracked_files() -> set[str]:
    """Get all files tracked by git."""
    try:
        result = subprocess.run(
            ["git", "ls-files"],
            capture_output=True, text=True, check=True,
        )
        return set(result.stdout.strip().split("\n")) - {""}
    except subprocess.CalledProcessError:
        return set()


def get_staged_files() -> set[str]:
    """Get files staged for commit."""
    try:
        result = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, check=True,
        )
        return set(result.stdout.strip().split("\n")) - {""}
    except subprocess.CalledProcessError:
        return set()


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------

def load_config() -> dict:
    """Load claude_md config from relationships.yaml."""
    try:
        import yaml  # noqa: PLC0415
        # Try relative to script location first, then CWD
        script_dir = Path(__file__).resolve().parent
        config_path = script_dir / "relationships.yaml"
        if not config_path.exists():
            config_path = Path("scripts/relationships.yaml")
        if config_path.exists():
            data = yaml.safe_load(config_path.read_text())
            return data.get("claude_md", {})
    except Exception:
        pass
    return {}


def get_exempt_dirs(config: dict) -> list[str]:
    return config.get("exempt_dirs", DEFAULT_EXEMPT_DIRS)


def get_exempt_files(config: dict) -> list[str]:
    return config.get("exempt_files", DEFAULT_EXEMPT_FILES)


# ---------------------------------------------------------------------------
# Directory discovery
# ---------------------------------------------------------------------------

def is_dir_exempt(dir_path: str, exempt_patterns: list[str]) -> bool:
    """Check if a directory matches any exemption pattern."""
    normalized = dir_path.rstrip("/") + "/"
    for pattern in exempt_patterns:
        pattern_norm = pattern.rstrip("/") + "/"
        if fnmatch.fnmatch(normalized, pattern_norm):
            return True
        if fnmatch.fnmatch(dir_path, pattern.rstrip("/")):
            return True
    return False


def is_file_exempt(filename: str, exempt_patterns: list[str]) -> bool:
    """Check if a filename matches any exemption pattern."""
    for pattern in exempt_patterns:
        if fnmatch.fnmatch(filename, pattern):
            return True
    return False


def is_coverage_exempt(dir_path: str, filename: str) -> bool:
    """Check if a file is exempt from coverage in its specific directory."""
    for dir_pattern, file_patterns in COVERAGE_EXEMPT_PATTERNS.items():
        if dir_path == dir_pattern or (dir_pattern and dir_path.startswith(dir_pattern + "/")):
            for fp in file_patterns:
                if fnmatch.fnmatch(filename, fp):
                    return True
    return False


def build_directory_map(tracked_files: set[str]) -> dict[str, list[str]]:
    """Build map of directory -> list of directly contained files."""
    dir_map: dict[str, list[str]] = {}
    for filepath in tracked_files:
        parent = str(Path(filepath).parent)
        if parent == ".":
            parent = ""
        filename = Path(filepath).name
        dir_map.setdefault(parent, []).append(filename)
    return dir_map


# ---------------------------------------------------------------------------
# CLAUDE.md parsing
# ---------------------------------------------------------------------------

def looks_like_filename(text: str) -> bool:
    """Check if text looks like a filename or directory reference."""
    text = text.strip().rstrip("/")
    if not text:
        return False
    # Has a file extension
    if "." in text and not text.startswith("."):
        ext = text.rsplit(".", 1)[-1]
        if ext.isalpha() and len(ext) <= 6:
            return True
    # Ends with / (directory)
    if text.endswith("/"):
        return True
    # Contains only valid path characters and has no spaces
    if re.match(r"^[\w./_-]+$", text) and " " not in text:
        # Has underscore or dot (likely a filename, not a word)
        if "_" in text or "." in text:
            return True
    return False


def parse_claude_md(content: str) -> set[str]:
    """Extract file/directory references from a CLAUDE.md file.

    Parses:
    - Markdown table first-column values that look like filenames
    - ASCII tree blocks (├── and └── lines)
    """
    refs: set[str] = set()

    # Pattern: markdown table row — extract first column value
    table_row_re = re.compile(
        r"^\|"
        r"\s*`?([^`|]+?)`?\s*"
        r"\|",
    )

    # Pattern: ASCII tree line
    tree_re = re.compile(r"^[\s│]*[├└]──\s+(.+?)(?:\s+#.*)?$")

    # Skip table header separator rows
    header_sep_re = re.compile(r"^\|\s*[-:]+\s*\|")

    # Common table header values to skip
    header_values = {
        "file", "directory", "script", "hook", "pattern",
        "type", "doc", "document", "module", "test file",
        "what", "where", "key files", "source", "location",
        "method", "purpose", "name", "description", "status",
        "decision", "choice", "rationale", "content", "when",
        "priority", "bypass", "consequence", "use", "not", "why",
    }

    for line in content.split("\n"):
        line = line.strip()

        if header_sep_re.match(line):
            continue

        # Try table row
        m = table_row_re.match(line)
        if m:
            ref = m.group(1).strip()
            if ref.lower() in header_values:
                continue
            if looks_like_filename(ref):
                refs.add(ref)
            continue

        # Try tree line
        m = tree_re.match(line)
        if m:
            ref = m.group(1).strip()
            if ref:
                refs.add(ref)

    return refs


def normalize_ref(ref: str) -> str:
    """Normalize a parsed reference for matching against filenames."""
    ref = ref.rstrip("/")
    return Path(ref).name if "/" not in ref else ref


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class Violation:
    def __init__(self, directory: str, kind: str, details: list[str]):
        self.directory = directory
        self.kind = kind
        self.details = details


def check_existence(
    dir_map: dict[str, list[str]],
    exempt_dirs: list[str],
    exempt_files: list[str],
) -> list[Violation]:
    """Check that directories with enough files have a CLAUDE.md."""
    violations = []
    for dir_path, files in sorted(dir_map.items()):
        if not dir_path:
            continue
        if is_dir_exempt(dir_path, exempt_dirs):
            continue

        non_exempt = [f for f in files if not is_file_exempt(f, exempt_files)]
        if len(non_exempt) < MIN_FILES_FOR_EXISTENCE:
            continue

        claude_path = Path(dir_path) / "CLAUDE.md"
        if not claude_path.exists():
            violations.append(Violation(
                dir_path, "missing_claude_md",
                [f"Directory has {len(non_exempt)} tracked files but no CLAUDE.md"],
            ))
    return violations


def check_coverage(
    dir_map: dict[str, list[str]],
    exempt_dirs: list[str],
    exempt_files: list[str],
) -> list[Violation]:
    """Check that CLAUDE.md files reference all tracked files."""
    violations = []
    for dir_path, files in sorted(dir_map.items()):
        if is_dir_exempt(dir_path, exempt_dirs):
            continue

        claude_path = Path(dir_path) / "CLAUDE.md" if dir_path else Path("CLAUDE.md")
        if not claude_path.exists():
            continue

        content = claude_path.read_text()
        refs = parse_claude_md(content)

        # Build set of normalized reference names for matching
        ref_names: set[str] = set()
        for ref in refs:
            ref_names.add(normalize_ref(ref))
            ref_names.add(ref.rstrip("/"))

        # Check each tracked file
        non_exempt = [f for f in files if not is_file_exempt(f, exempt_files)]

        uncovered = []
        for filename in sorted(non_exempt):
            # Skip files exempt by directory-specific pattern
            if is_coverage_exempt(dir_path, filename):
                continue

            name_no_ext = Path(filename).stem
            if (
                filename not in ref_names
                and name_no_ext not in ref_names
                and not any(filename in r for r in ref_names)
                and filename not in content
            ):
                uncovered.append(filename)

        if uncovered:
            violations.append(Violation(
                dir_path or "(root)", "uncovered_files", uncovered,
            ))

    return violations


def check_phantom(
    dir_map: dict[str, list[str]],
    exempt_dirs: list[str],
) -> list[Violation]:
    """Check that CLAUDE.md doesn't reference files that don't exist."""
    violations = []
    for dir_path, files in sorted(dir_map.items()):
        if is_dir_exempt(dir_path, exempt_dirs):
            continue

        claude_path = Path(dir_path) / "CLAUDE.md" if dir_path else Path("CLAUDE.md")
        if not claude_path.exists():
            continue

        content = claude_path.read_text()
        refs = parse_claude_md(content)
        file_set = set(files)

        # Also include subdirectory names
        base = Path(dir_path) if dir_path else Path(".")
        subdirs = set()
        if base.exists():
            for child in base.iterdir():
                if child.is_dir():
                    subdirs.add(child.name)
                    subdirs.add(child.name + "/")

        all_names = file_set | subdirs

        phantom = []
        for ref in sorted(refs):
            name = normalize_ref(ref)
            name_stripped = name.rstrip("/")

            # Only check refs that look like they're for THIS directory
            if "/" in ref:
                continue

            # Must look like a real filename
            if not looks_like_filename(ref):
                continue

            # Skip glob patterns (e.g., test_*.py, NNNN-*.md)
            if "*" in ref or "..." in ref:
                continue

            if (
                name not in all_names
                and name_stripped not in all_names
                and name_stripped + "/" not in all_names
                and not any(name_stripped in n for n in all_names)
            ):
                phantom.append(ref)

        if phantom:
            violations.append(Violation(
                dir_path or "(root)", "phantom_refs", phantom,
            ))

    return violations


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def report_violations(violations: list[Violation], suggest: bool = False) -> None:
    """Print violation report."""
    if not violations:
        return

    missing = [v for v in violations if v.kind == "missing_claude_md"]
    uncovered = [v for v in violations if v.kind == "uncovered_files"]
    phantom = [v for v in violations if v.kind == "phantom_refs"]

    if missing:
        print("=" * 60)
        print("MISSING CLAUDE.MD (must fix)")
        print("=" * 60)
        print()
        for v in missing:
            print(f"  {v.directory}/")
            for d in v.details:
                print(f"    {d}")
            if suggest:
                print(f"    → Create {v.directory}/CLAUDE.md with file listing")
            print()

    if uncovered:
        print("=" * 60)
        print("UNCOVERED FILES (must fix)")
        print("=" * 60)
        print()
        for v in uncovered:
            print(f"  {v.directory}/CLAUDE.md missing:")
            for f in v.details[:10]:
                print(f"    - {f}")
            if len(v.details) > 10:
                print(f"    ... and {len(v.details) - 10} more")
            if suggest:
                print(f"    → Add these files to {v.directory}/CLAUDE.md")
            print()

    if phantom:
        print("=" * 60)
        print("PHANTOM REFERENCES (warning)")
        print("=" * 60)
        print()
        for v in phantom:
            print(f"  {v.directory}/CLAUDE.md references non-existent:")
            for f in v.details[:10]:
                print(f"    - {f}")
            if len(v.details) > 10:
                print(f"    ... and {len(v.details) - 10} more")
            print()


def print_fix_stubs(violations: list[Violation]) -> None:
    """Print stub table rows for uncovered files."""
    uncovered = [v for v in violations if v.kind == "uncovered_files"]
    if not uncovered:
        print("No uncovered files found.")
        return

    for v in uncovered:
        print(f"\n## {v.directory}/CLAUDE.md — add these rows:\n")
        for f in sorted(v.details):
            print(f"| `{f}` | TODO |")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(
        description="CLAUDE.md coverage validation and enforcement",
    )
    parser.add_argument(
        "--staged", action="store_true",
        help="Check only directories touched by staged files (pre-commit)",
    )
    parser.add_argument(
        "--all", action="store_true",
        help="Check all directories in the project",
    )
    parser.add_argument(
        "--strict", action="store_true",
        help="Exit 1 on violations",
    )
    parser.add_argument(
        "--suggest", action="store_true",
        help="Show suggestions for fixing violations",
    )
    parser.add_argument(
        "--fix-stub", action="store_true",
        help="Print stub table rows for uncovered files",
    )
    args = parser.parse_args()

    if not args.staged and not args.all:
        args.all = True

    config = load_config()
    exempt_dirs = get_exempt_dirs(config)
    exempt_files = get_exempt_files(config)

    all_tracked = get_tracked_files()
    dir_map = build_directory_map(all_tracked)

    if args.staged:
        staged = get_staged_files()
        if not staged:
            return 0

        touched_dirs: set[str] = set()
        for f in staged:
            parent = str(Path(f).parent)
            if parent == ".":
                parent = ""
            touched_dirs.add(parent)

        dir_map = {d: files for d, files in dir_map.items() if d in touched_dirs}

    violations: list[Violation] = []
    violations.extend(check_existence(dir_map, exempt_dirs, exempt_files))
    violations.extend(check_coverage(dir_map, exempt_dirs, exempt_files))
    violations.extend(check_phantom(dir_map, exempt_dirs))

    if args.fix_stub:
        if not violations:
            all_dir_map = build_directory_map(all_tracked)
            violations = check_coverage(all_dir_map, exempt_dirs, exempt_files)
        print_fix_stubs(violations)
        return 0

    if violations:
        report_violations(violations, suggest=args.suggest)

        blocking = [
            v for v in violations
            if v.kind in {"missing_claude_md", "uncovered_files"}
        ]
        if blocking:
            total = sum(len(v.details) for v in blocking)
            print(f"Total: {len(blocking)} directories with {total} issues")
            print()
            if args.suggest:
                print("Run with --fix-stub to get copy-paste table rows.")
            return 1 if args.strict else 0

    if not violations:
        print("CLAUDE.md validation passed.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
