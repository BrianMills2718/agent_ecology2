#!/usr/bin/env python3
"""Implementation Understanding Quiz (Plan #296).

Generates quizzes on changed files to verify user comprehension of:
- What the code does
- Tradeoffs made in implementation
- Whether implementation matches intentions

Usage:
    python scripts/implementation_quiz.py [--branch BRANCH] [--base BASE]
    python scripts/implementation_quiz.py --file FILE [FILE ...]
"""

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


def get_config() -> dict[str, Any]:
    """Load quiz configuration from meta-process.yaml."""
    config_path = Path("meta-process.yaml")
    if not config_path.exists():
        return {"quiz": {"integration": "manual", "min_lines_changed": 0}}

    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    return config.get("quiz", {"integration": "manual", "min_lines_changed": 0})


def get_changed_files(branch: str = "HEAD", base: str = "main") -> list[dict[str, Any]]:
    """Get list of changed files with stats."""
    # Get list of changed files with line counts
    result = subprocess.run(
        ["git", "diff", "--numstat", f"{base}...{branch}"],
        capture_output=True,
        text=True,
    )

    files = []
    for line in result.stdout.strip().split("\n"):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) >= 3:
            added = int(parts[0]) if parts[0] != "-" else 0
            removed = int(parts[1]) if parts[1] != "-" else 0
            filepath = parts[2]
            files.append({
                "path": filepath,
                "added": added,
                "removed": removed,
                "total_changed": added + removed,
            })

    return sorted(files, key=lambda x: x["total_changed"], reverse=True)


def get_file_diff(filepath: str, branch: str = "HEAD", base: str = "main") -> str:
    """Get the diff for a specific file."""
    result = subprocess.run(
        ["git", "diff", f"{base}...{branch}", "--", filepath],
        capture_output=True,
        text=True,
    )
    return result.stdout


def get_file_content(filepath: str, branch: str = "HEAD") -> str:
    """Get file content at a specific branch."""
    result = subprocess.run(
        ["git", "show", f"{branch}:{filepath}"],
        capture_output=True,
        text=True,
    )
    return result.stdout


def render_changes_chart(files: list[dict[str, Any]]) -> str:
    """Render ASCII chart of changes by file."""
    if not files:
        return "No files changed."

    max_lines = max(f["total_changed"] for f in files)
    max_path_len = min(40, max(len(f["path"]) for f in files))
    chart_width = 40

    lines = [
        "┌" + "─" * (max_path_len + 2) + "┬" + "─" * (chart_width + 2) + "┬" + "─" * 8 + "┐",
        "│ " + "File".ljust(max_path_len) + " │ " + "Changes".center(chart_width) + " │ " + "Lines".center(6) + " │",
        "├" + "─" * (max_path_len + 2) + "┼" + "─" * (chart_width + 2) + "┼" + "─" * 8 + "┤",
    ]

    for f in files[:15]:  # Limit to top 15 files
        path = f["path"]
        if len(path) > max_path_len:
            path = "..." + path[-(max_path_len - 3):]

        bar_len = int((f["total_changed"] / max_lines) * chart_width) if max_lines > 0 else 0
        bar_len = max(1, bar_len)  # At least 1 char

        # Green for added, red for removed
        added_ratio = f["added"] / f["total_changed"] if f["total_changed"] > 0 else 0.5
        green_len = int(bar_len * added_ratio)
        red_len = bar_len - green_len

        bar = "+" * green_len + "-" * red_len
        bar = bar.ljust(chart_width)

        lines.append(f"│ {path.ljust(max_path_len)} │ {bar} │ {str(f['total_changed']).center(6)} │")

    if len(files) > 15:
        lines.append(f"│ {'... and ' + str(len(files) - 15) + ' more files'.ljust(max_path_len)} │ {' ' * chart_width} │ {''.center(6)} │")

    lines.append("└" + "─" * (max_path_len + 2) + "┴" + "─" * (chart_width + 2) + "┴" + "─" * 8 + "┘")

    return "\n".join(lines)


def render_file_structure_chart(files: list[dict[str, Any]]) -> str:
    """Render ASCII tree of changed files by directory."""
    from collections import defaultdict

    # Group by directory
    by_dir: dict[str, list[str]] = defaultdict(list)
    for f in files:
        path = Path(f["path"])
        dir_path = str(path.parent) if path.parent != Path(".") else "(root)"
        by_dir[dir_path].append(path.name)

    lines = ["Changed file structure:", ""]

    dirs = sorted(by_dir.keys())
    for i, dir_path in enumerate(dirs):
        is_last_dir = i == len(dirs) - 1
        prefix = "└── " if is_last_dir else "├── "
        lines.append(f"{prefix}{dir_path}/")

        filenames = sorted(by_dir[dir_path])
        for j, filename in enumerate(filenames):
            is_last_file = j == len(filenames) - 1
            dir_prefix = "    " if is_last_dir else "│   "
            file_prefix = "└── " if is_last_file else "├── "
            lines.append(f"{dir_prefix}{file_prefix}{filename}")

    return "\n".join(lines)


def generate_quiz_prompt(filepath: str, diff: str, content: str) -> str:
    """Generate the prompt for quiz generation."""
    return f"""Analyze this code change and generate a comprehension quiz.

FILE: {filepath}

DIFF:
```
{diff[:3000]}  # Truncate long diffs
```

CURRENT CONTENT (after change):
```
{content[:5000]}  # Truncate long files
```

Generate a quiz with 3-5 questions that verify the user:
1. Understands what this code DOES (comprehension)
2. Understands WHY it was done this way (tradeoffs)
3. Confirms this matches their INTENTION (alignment)

For each question:
- Use multiple choice (A/B/C/D) where possible
- Include an "explain" option for open-ended understanding
- Note the correct answer

Use ASCII diagrams where helpful to illustrate:
- Data flow
- State transitions
- Architecture relationships
- Before/after comparisons

Format as YAML:
```yaml
file: {filepath}
summary: |
  Brief description of what changed
diagram: |
  ASCII diagram if helpful (optional)
questions:
  - type: multiple_choice
    category: comprehension|tradeoff|alignment
    question: "What does X do?"
    options:
      a: "Option A"
      b: "Option B"
      c: "Option C"
      d: "Option D"
    correct: "b"
    explanation: "Why B is correct"
  - type: open_ended
    category: comprehension|tradeoff|alignment
    question: "Explain why..."
    key_points:
      - "Point 1"
      - "Point 2"
```
"""


def print_quiz_header(files: list[dict[str, Any]]) -> None:
    """Print quiz header with overview."""
    total_added = sum(f["added"] for f in files)
    total_removed = sum(f["removed"] for f in files)

    print("\n" + "=" * 70)
    print("  IMPLEMENTATION UNDERSTANDING QUIZ")
    print("=" * 70)
    print()
    print(f"  Files changed: {len(files)}")
    print(f"  Lines added:   +{total_added}")
    print(f"  Lines removed: -{total_removed}")
    print()
    print(render_changes_chart(files))
    print()
    print(render_file_structure_chart(files))
    print()
    print("-" * 70)
    print("  This quiz verifies your understanding of the changes.")
    print("  Answer honestly - misalignment is valuable feedback!")
    print("-" * 70)
    print()


def run_interactive_quiz(files: list[dict[str, Any]], branch: str, base: str) -> dict[str, Any]:
    """Run interactive quiz on changed files."""
    print_quiz_header(files)

    results: dict[str, Any] = {
        "files_quizzed": [],
        "total_questions": 0,
        "understood": 0,
        "misaligned": 0,
        "needs_discussion": [],
    }

    for f in files:
        filepath = f["path"]

        # Skip non-code files
        if not any(filepath.endswith(ext) for ext in [".py", ".yaml", ".yml", ".md", ".json"]):
            continue

        print(f"\n{'=' * 70}")
        print(f"  FILE: {filepath}")
        print(f"  Changes: +{f['added']} / -{f['removed']}")
        print("=" * 70)

        diff = get_file_diff(filepath, branch, base)

        # Show diff summary
        print("\nDiff preview:")
        print("-" * 40)
        diff_lines = diff.split("\n")[:30]
        for line in diff_lines:
            if line.startswith("+") and not line.startswith("+++"):
                print(f"  \033[32m{line}\033[0m")  # Green
            elif line.startswith("-") and not line.startswith("---"):
                print(f"  \033[31m{line}\033[0m")  # Red
            else:
                print(f"  {line}")
        if len(diff.split("\n")) > 30:
            print(f"  ... ({len(diff.split(chr(10))) - 30} more lines)")
        print("-" * 40)

        # Ask comprehension questions
        print("\n  COMPREHENSION CHECK:")
        print()

        q1 = input("  1. In your own words, what does this change DO?\n     > ")
        results["total_questions"] += 1

        q2 = input("\n  2. What TRADEOFF or design decision was made here?\n     > ")
        results["total_questions"] += 1

        q3 = input("\n  3. Does this match your INTENTION? (yes/no/partially)\n     > ").lower().strip()
        results["total_questions"] += 1

        if q3 in ["yes", "y"]:
            results["understood"] += 1
        elif q3 in ["no", "n"]:
            results["misaligned"] += 1
            results["needs_discussion"].append({
                "file": filepath,
                "reason": input("     What's different from your intention?\n     > "),
            })
        else:
            concern = input("     What aspect is unclear or partially misaligned?\n     > ")
            if concern:
                results["needs_discussion"].append({
                    "file": filepath,
                    "reason": concern,
                })

        results["files_quizzed"].append(filepath)

        print()
        continue_quiz = input("  Continue to next file? (yes/no) [yes]: ").lower().strip()
        if continue_quiz in ["no", "n"]:
            break

    return results


def print_quiz_results(results: dict[str, Any]) -> None:
    """Print quiz results summary."""
    print("\n" + "=" * 70)
    print("  QUIZ RESULTS")
    print("=" * 70)

    files_count = len(results["files_quizzed"])

    # ASCII result chart
    if files_count > 0:
        understood_pct = (results["understood"] / files_count) * 100
        misaligned_pct = (results["misaligned"] / files_count) * 100
        partial_pct = 100 - understood_pct - misaligned_pct

        bar_width = 40
        understood_bar = int(understood_pct / 100 * bar_width)
        misaligned_bar = int(misaligned_pct / 100 * bar_width)
        partial_bar = bar_width - understood_bar - misaligned_bar

        print()
        print("  Alignment:")
        print(f"  [{'█' * understood_bar}{'░' * partial_bar}{'▒' * misaligned_bar}]")
        print(f"   █ Aligned: {results['understood']}/{files_count} ({understood_pct:.0f}%)")
        print(f"   ░ Partial: {files_count - results['understood'] - results['misaligned']}/{files_count}")
        print(f"   ▒ Misaligned: {results['misaligned']}/{files_count} ({misaligned_pct:.0f}%)")

    print()
    print(f"  Files quizzed: {files_count}")
    print(f"  Total questions: {results['total_questions']}")

    if results["needs_discussion"]:
        print()
        print("  ⚠ NEEDS DISCUSSION:")
        print("  " + "-" * 40)
        for item in results["needs_discussion"]:
            print(f"  • {item['file']}")
            print(f"    {item['reason']}")
        print("  " + "-" * 40)

    print()
    if results["misaligned"] > 0:
        print("  RECOMMENDATION: Review misaligned files before merge.")
    elif results["needs_discussion"]:
        print("  RECOMMENDATION: Discuss partial alignments before merge.")
    else:
        print("  ✓ All changes appear to match your intentions.")

    print("=" * 70)


def main() -> int:
    parser = argparse.ArgumentParser(description="Implementation Understanding Quiz")
    parser.add_argument("--branch", default="HEAD", help="Branch to quiz")
    parser.add_argument("--base", default="main", help="Base branch to compare against")
    parser.add_argument("--file", nargs="+", help="Specific files to quiz")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be quizzed")
    parser.add_argument("--config", action="store_true", help="Show current configuration")
    args = parser.parse_args()

    config = get_config()

    if args.config:
        print("Quiz configuration:")
        print(yaml.dump(config, default_flow_style=False))
        return 0

    # Get changed files
    if args.file:
        files = [{"path": f, "added": 0, "removed": 0, "total_changed": 0} for f in args.file]
    else:
        files = get_changed_files(args.branch, args.base)

    # Filter by min_lines_changed
    min_lines = config.get("min_lines_changed", 0)
    if min_lines > 0:
        files = [f for f in files if f["total_changed"] >= min_lines]

    if not files:
        print("No files to quiz.")
        return 0

    if args.dry_run:
        print("Would quiz the following files:")
        print(render_changes_chart(files))
        return 0

    # Run interactive quiz
    results = run_interactive_quiz(files, args.branch, args.base)
    print_quiz_results(results)

    # Return non-zero if misaligned (for CI integration)
    if results["misaligned"] > 0:
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
