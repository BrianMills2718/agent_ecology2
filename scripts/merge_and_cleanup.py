#!/usr/bin/env python3
"""Merge a PR and clean up the branch."""

import argparse
import subprocess
import sys


def run(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, capture_output=True, text=True, check=check)


def main() -> int:
    parser = argparse.ArgumentParser(description="Merge PR and clean up branch")
    parser.add_argument("--branch", required=True, help="Branch name")
    parser.add_argument("--pr", required=True, type=int, help="PR number")
    args = parser.parse_args()

    # Verify we're on main
    result = run(["git", "branch", "--show-current"])
    if result.stdout.strip() != "main":
        print("ERROR: Must be on main branch to merge. Run: git checkout main")
        return 1

    # Merge the PR
    print(f"Merging PR #{args.pr}...")
    result = run(["gh", "pr", "merge", str(args.pr), "--squash", "--delete-branch"], check=False)
    if result.returncode != 0:
        print(f"ERROR: Failed to merge PR #{args.pr}")
        print(result.stderr)
        return 1
    print(f"PR #{args.pr} merged.")

    # Pull latest main
    print("Pulling latest main...")
    run(["git", "pull", "--ff-only"])

    # Clean up local branch — use -D because squash-merge creates new hashes
    # so git branch -d (which checks merge status) fails on squash-merged branches
    result = run(["git", "branch", "-D", args.branch], check=False)
    if result.returncode == 0:
        print(f"Deleted local branch {args.branch}.")
    else:
        # Branch may not exist locally, which is fine
        if "not found" not in result.stderr:
            print(f"Warning: could not delete local branch {args.branch}: {result.stderr.strip()}")

    print(f"\nDone! PR #{args.pr} merged, branch {args.branch} cleaned up.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
