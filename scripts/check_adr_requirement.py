#!/usr/bin/env python3
"""Check if changes to core files require an ADR reference.

Plan #43: Comprehensive Meta-Enforcement - Phase 2 CI Checks.

Core files (kernel-level code) require architectural decisions to be
documented in ADRs. This script checks that commits affecting these
files reference an ADR.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

# Core files that require ADR references when modified
CORE_FILES = [
    "src/world/ledger.py",
    "src/world/executor.py",
    "src/world/artifacts.py",
    "src/world/genesis.py",
]

# Pattern to match ADR references in commit messages
ADR_PATTERN = re.compile(r"ADR[-_]?\d{4}", re.IGNORECASE)


def get_changed_files(base_ref: str = "origin/main") -> list[str]:
    """Get files changed since base_ref.

    Args:
        base_ref: Git reference to compare against (default: origin/main).

    Returns:
        List of changed file paths.
    """
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", base_ref, "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def get_commit_messages(base_ref: str = "origin/main") -> list[str]:
    """Get commit messages since base_ref.

    Args:
        base_ref: Git reference to compare against (default: origin/main).

    Returns:
        List of commit messages.
    """
    try:
        result = subprocess.run(
            ["git", "log", "--format=%s%n%b", f"{base_ref}..HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return [result.stdout] if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def requires_adr(changed_files: list[str]) -> list[str]:
    """Check if any changed files require an ADR.

    Args:
        changed_files: List of changed file paths.

    Returns:
        List of core files that were changed.
    """
    return [f for f in changed_files if f in CORE_FILES]


def has_adr_reference(messages: list[str]) -> bool:
    """Check if any commit message references an ADR.

    Args:
        messages: List of commit messages to check.

    Returns:
        True if any message contains an ADR reference.
    """
    full_text = "\n".join(messages)
    return bool(ADR_PATTERN.search(full_text))


def check_adr_requirement(
    changed_files: list[str] | None = None,
    commit_messages: list[str] | None = None,
    base_ref: str = "origin/main",
) -> tuple[bool, str]:
    """Check if changes require an ADR and whether one is referenced.

    Args:
        changed_files: Override for changed files (for testing).
        commit_messages: Override for commit messages (for testing).
        base_ref: Git reference for comparison.

    Returns:
        Tuple of (passes, message).
    """
    if changed_files is None:
        changed_files = get_changed_files(base_ref)

    if commit_messages is None:
        commit_messages = get_commit_messages(base_ref)

    core_changes = requires_adr(changed_files)

    if not core_changes:
        return True, "No core files changed - ADR not required"

    if has_adr_reference(commit_messages):
        return True, f"Core files changed ({', '.join(core_changes)}), ADR referenced"

    return (
        False,
        f"Core files changed ({', '.join(core_changes)}) but no ADR reference found.\n"
        "Please reference an existing ADR (e.g., 'ADR-0001') or create a new one.",
    )


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check if changes to core files require an ADR reference"
    )
    parser.add_argument(
        "--base",
        "-b",
        default="origin/main",
        help="Base ref to compare against (default: origin/main)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit with error code 1 if ADR required but not referenced",
    )

    args = parser.parse_args()

    passes, message = check_adr_requirement(base_ref=args.base)

    if passes:
        print(f"✓ {message}")
        return 0
    else:
        if args.strict:
            print(f"✗ {message}")
            return 1
        else:
            print(f"⚠ Warning: {message}")
            return 0


if __name__ == "__main__":
    sys.exit(main())
