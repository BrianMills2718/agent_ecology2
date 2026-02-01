#!/usr/bin/env python3
"""Compare plan's declared Files Affected against actual git diff.

Reports scope creep (undeclared changes) and plan drift (declared but untouched files)
at three severity levels.

Usage:
    # Check current branch against its plan
    python scripts/check_plan_diff.py --plan 249

    # Check specific branch
    python scripts/check_plan_diff.py --plan 249 --branch plan-249-plan-to-diff

    # Strict mode (exit non-zero on HIGH findings)
    python scripts/check_plan_diff.py --plan 249 --strict

    # Machine-readable output
    python scripts/check_plan_diff.py --plan 249 --json
"""

import argparse
import fnmatch
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

# Import from parse_plan.py
sys.path.insert(0, str(Path(__file__).parent))
from parse_plan import find_plan_file, parse_files_affected

# Files commonly touched across plans that aren't worth flagging
BUILTIN_WHITELIST = [
    "tests/conftest.py",
    "*/__init__.py",
    "__init__.py",
    ".claude/CONTEXT.md",
    "config/schema.yaml",
    "docs/plans/CLAUDE.md",
    "docs/plans/*.md",
    "*.pyc",
    ".claim.yaml",
]


@dataclass
class Finding:
    """A discrepancy between plan declarations and actual diff."""

    severity: str  # HIGH, MEDIUM, WARN
    path: str
    message: str


def is_whitelisted(path: str, whitelist: list[str] | None = None) -> bool:
    """Check if a path matches any whitelist pattern."""
    patterns = BUILTIN_WHITELIST + (whitelist or [])
    for pattern in patterns:
        if fnmatch.fnmatch(path, pattern):
            return True
        # Also check basename for patterns like "__init__.py"
        if fnmatch.fnmatch(Path(path).name, pattern):
            return True
    return False


def get_diff_files(branch: str | None = None, base: str = "main") -> list[str]:
    """Get list of files changed between base and branch."""
    if branch:
        diff_range = f"{base}...{branch}"
    else:
        diff_range = f"{base}...HEAD"

    result = subprocess.run(
        ["git", "diff", "--name-only", diff_range],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []
    return [f for f in result.stdout.strip().split("\n") if f]


def classify_findings(
    declared_files: list[dict],
    diff_files: list[str],
    whitelist: list[str] | None = None,
) -> list[Finding]:
    """Compare declared files against diff and return findings."""
    findings: list[Finding] = []
    declared_paths = {entry["path"] for entry in declared_files}

    # Check diff files against declarations (scope creep)
    for path in diff_files:
        if is_whitelisted(path, whitelist):
            continue
        if path not in declared_paths:
            if path.startswith("src/"):
                findings.append(Finding(
                    severity="HIGH",
                    path=path,
                    message="Undeclared production code change (scope creep)",
                ))
            elif path.startswith("tests/"):
                findings.append(Finding(
                    severity="MEDIUM",
                    path=path,
                    message="Undeclared test change (usually benign)",
                ))
            else:
                findings.append(Finding(
                    severity="MEDIUM",
                    path=path,
                    message="Undeclared file change",
                ))

    # Check declared files against diff (plan drift)
    for entry in declared_files:
        path = entry["path"]
        if path not in diff_files:
            findings.append(Finding(
                severity="WARN",
                path=path,
                message=f"Declared as ({entry.get('action', 'modify')}) but not in diff (plan drift)",
            ))

    return findings


def check_plan_diff(
    plan_number: int,
    branch: str | None = None,
    strict: bool = False,
    whitelist: list[str] | None = None,
) -> tuple[list[Finding], int]:
    """Main logic: parse plan, get diff, compare.

    Returns (findings, exit_code).
    """
    # Find and parse plan
    plan_file = find_plan_file(plan_number)
    if not plan_file or not plan_file.exists():
        print(f"Plan file not found for plan #{plan_number}", file=sys.stderr)
        return [], 1

    content = plan_file.read_text()
    declared_files = parse_files_affected(content)

    if not declared_files:
        print(
            f"Plan #{plan_number}: No 'Files Affected' section found — skipping diff check",
            file=sys.stderr,
        )
        return [], 0

    # Get actual diff
    diff_files = get_diff_files(branch)
    if not diff_files:
        print(f"No diff found for branch {branch or 'HEAD'}", file=sys.stderr)
        return [], 0

    # Compare
    findings = classify_findings(declared_files, diff_files, whitelist)

    # Determine exit code
    has_high = any(f.severity == "HIGH" for f in findings)
    exit_code = 1 if (strict and has_high) else 0

    return findings, exit_code


def format_findings(findings: list[Finding], plan_number: int) -> str:
    """Format findings for human-readable output."""
    if not findings:
        return f"Plan #{plan_number}: All files align with declarations"

    lines = [f"Plan #{plan_number}: {len(findings)} finding(s)"]
    lines.append("")

    # Group by severity
    for severity in ["HIGH", "MEDIUM", "WARN"]:
        group = [f for f in findings if f.severity == severity]
        if not group:
            continue
        icon = {"HIGH": "!!!", "MEDIUM": " ! ", "WARN": " ? "}[severity]
        for finding in group:
            lines.append(f"  [{icon}] {severity}: {finding.path}")
            lines.append(f"         {finding.message}")

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare plan declarations against actual git diff",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--plan", "-p", type=int, required=True, help="Plan number")
    parser.add_argument("--branch", "-b", type=str, help="Branch name (default: current)")
    parser.add_argument(
        "--strict", action="store_true", help="Exit non-zero on HIGH findings"
    )
    parser.add_argument("--json", "-j", action="store_true", help="JSON output")
    parser.add_argument(
        "--whitelist", type=str, nargs="*", help="Additional whitelist patterns"
    )

    args = parser.parse_args()

    findings, exit_code = check_plan_diff(
        plan_number=args.plan,
        branch=args.branch,
        strict=args.strict,
        whitelist=args.whitelist,
    )

    if args.json:
        output = {
            "plan": args.plan,
            "branch": args.branch,
            "findings": [
                {"severity": f.severity, "path": f.path, "message": f.message}
                for f in findings
            ],
            "exit_code": exit_code,
        }
        print(json.dumps(output, indent=2))
    else:
        output_text = format_findings(findings, args.plan)
        if output_text:
            print(output_text)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
