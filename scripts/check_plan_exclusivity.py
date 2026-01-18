#!/usr/bin/env python3
"""Check that plan numbers are exclusive across open PRs.

Plan #72: Enforce that only one open PR can use a given plan number.

Usage:
    python scripts/check_plan_exclusivity.py [--pr PR_NUMBER]

If --pr is not specified, attempts to detect from environment (GitHub Actions).
"""

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Set, List, Dict, Any, Optional


def extract_plan_numbers_from_commits(commit_messages: List[str]) -> Set[int]:
    """Extract plan numbers from commit messages.
    
    Args:
        commit_messages: List of commit message strings
        
    Returns:
        Set of plan numbers found (empty if only trivial/unplanned commits)
    """
    plan_numbers: Set[int] = set()
    plan_pattern = re.compile(r'\[Plan #(\d+)\]', re.IGNORECASE)
    
    for message in commit_messages:
        # Skip trivial commits
        if '[Trivial]' in message:
            continue
        
        match = plan_pattern.search(message)
        if match:
            plan_numbers.add(int(match.group(1)))
    
    return plan_numbers


def get_commit_messages_for_pr() -> List[str]:
    """Get commit messages for commits in this PR (compared to main).
    
    Returns:
        List of commit message first lines
    """
    result = subprocess.run(
        ["git", "log", "origin/main..HEAD", "--oneline"],
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode != 0:
        print(f"Warning: Could not get commits: {result.stderr}", file=sys.stderr)
        return []
    
    return [line.split(" ", 1)[1] if " " in line else line 
            for line in result.stdout.strip().split("\n") 
            if line.strip()]


def get_open_prs_with_plan_number(plan_number: int, exclude_pr: Optional[int] = None) -> List[Dict[str, Any]]:
    """Query GitHub for open PRs that use the given plan number.
    
    Args:
        plan_number: The plan number to search for
        exclude_pr: PR number to exclude from results (current PR)
        
    Returns:
        List of PR info dicts with matching plan number
    """
    # Get all open PRs with their titles
    result = subprocess.run(
        ["gh", "pr", "list", "--state", "open", "--json", "number,title,headRefName"],
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode != 0:
        print(f"Warning: Could not query GitHub PRs: {result.stderr}", file=sys.stderr)
        return []
    
    try:
        prs = json.loads(result.stdout)
    except json.JSONDecodeError:
        print(f"Warning: Could not parse PR list", file=sys.stderr)
        return []
    
    # Filter to PRs with matching plan number
    plan_pattern = re.compile(rf'\[Plan #{plan_number}\]', re.IGNORECASE)
    matching_prs = []
    
    for pr in prs:
        # Skip the current PR
        if exclude_pr and pr["number"] == exclude_pr:
            continue
        
        if plan_pattern.search(pr.get("title", "")):
            matching_prs.append(pr)
    
    return matching_prs


def check_plan_exclusivity(plan_numbers: Set[int], current_pr: Optional[int] = None) -> List[Dict[str, Any]]:
    """Check if any plan numbers are already in use by other open PRs.
    
    Args:
        plan_numbers: Set of plan numbers used by current PR
        current_pr: Current PR number to exclude from conflict check
        
    Returns:
        List of conflicts, each with plan_number and conflicting_pr info
    """
    if not plan_numbers:
        return []  # No plan numbers to check (trivial-only)
    
    conflicts = []
    
    for plan_num in plan_numbers:
        conflicting_prs = get_open_prs_with_plan_number(plan_num, exclude_pr=current_pr)
        
        for pr in conflicting_prs:
            conflicts.append({
                "plan_number": plan_num,
                "conflicting_pr": pr["number"],
                "conflicting_title": pr.get("title", ""),
                "conflicting_branch": pr.get("headRefName", ""),
            })
    
    return conflicts


def get_current_pr_number() -> Optional[int]:
    """Try to get current PR number from GitHub Actions environment."""
    # GitHub Actions sets GITHUB_REF for PRs as refs/pull/123/merge
    github_ref = os.environ.get("GITHUB_REF", "")
    match = re.search(r'refs/pull/(\d+)/', github_ref)
    if match:
        return int(match.group(1))
    
    # Try gh pr view to get current PR
    result = subprocess.run(
        ["gh", "pr", "view", "--json", "number"],
        capture_output=True,
        text=True,
        check=False
    )
    
    if result.returncode == 0:
        try:
            data = json.loads(result.stdout)
            return data.get("number")
        except json.JSONDecodeError:
            pass
    
    return None


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check plan number exclusivity across open PRs"
    )
    parser.add_argument(
        "--pr",
        type=int,
        help="Current PR number (auto-detected if not specified)"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with error if conflicts found (CI mode)"
    )
    args = parser.parse_args()
    
    # Get current PR number
    current_pr = args.pr or get_current_pr_number()
    
    # Get commits for this PR
    commits = get_commit_messages_for_pr()
    if not commits:
        print("No commits found to check")
        return 0
    
    # Extract plan numbers
    plan_numbers = extract_plan_numbers_from_commits(commits)
    
    if not plan_numbers:
        print("No plan numbers found in commits (trivial-only PR)")
        return 0
    
    print(f"Checking plan numbers: {sorted(plan_numbers)}")
    if current_pr:
        print(f"Current PR: #{current_pr}")
    
    # Check for conflicts
    conflicts = check_plan_exclusivity(plan_numbers, current_pr)
    
    if conflicts:
        print("\n" + "=" * 60)
        print("PLAN NUMBER CONFLICTS DETECTED")
        print("=" * 60)
        for conflict in conflicts:
            print(f"\n  Plan #{conflict['plan_number']} is already in use by:")
            print(f"    PR #{conflict['conflicting_pr']}: {conflict['conflicting_title']}")
            print(f"    Branch: {conflict['conflicting_branch']}")
        print("\n" + "=" * 60)
        print("Each plan number can only be used by one open PR at a time.")
        print("Either:")
        print("  1. Close the conflicting PR first")
        print("  2. Use a different plan number for this work")
        print("  3. Coordinate with the other PR's author")
        print("=" * 60)
        
        if args.check:
            return 1
    else:
        print("✓ No plan number conflicts found")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
