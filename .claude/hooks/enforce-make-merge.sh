#!/bin/bash
# Block direct GitHub CLI merge and enforce proper merge workflow (Plan #115)
# Also blocks ANY worktree deletion commands from inside worktrees
# Also blocks direct script calls that bypass make targets
#
# Rules:
# 1. No direct GitHub merge CLI - must use make merge/finish
# 2. No direct python scripts/safe_worktree_remove.py - must use make worktree-remove
# 3. No direct python scripts/finish_pr.py - must use make finish
# 4. No merge/finish/worktree-remove from inside a worktree
# 5. Must cd to main FIRST (separate command), then run finish
#
# Exit codes:
#   0 - Allow the operation
#   2 - Block the operation

set -e

# Read the tool input from stdin
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [[ -z "$COMMAND" ]]; then
    exit 0  # No command, allow
fi

# Check if command contains direct GitHub CLI merge
if echo "$COMMAND" | grep -qE 'gh\s+pr\s+merge'; then
    PR_NUM=$(echo "$COMMAND" | grep -oE 'merge\s+[0-9]+' | grep -oE '[0-9]+' || echo "N")

    echo "BLOCKED: Direct GitHub CLI merge is not allowed" >&2
    echo "" >&2
    echo "This bypasses worktree auto-cleanup - orphan worktrees will accumulate." >&2
    echo "" >&2
    echo "Use the proper command instead:" >&2
    echo "  make merge PR=$PR_NUM" >&2
    exit 2
fi

# Block direct calls to safe_worktree_remove.py (must use make worktree-remove)
# This ensures the latest version from main is always used, not a stale worktree copy
# Pattern: matches command starting with or containing '&& python' or '; python' before the script
if echo "$COMMAND" | grep -qE '(^|&&|;|\|)\s*python[3]?\s+scripts/safe_worktree_remove\.py'; then
    WORKTREE=$(echo "$COMMAND" | grep -oE 'worktrees/[^ ]+' || echo "BRANCH")
    BRANCH=$(basename "$WORKTREE" 2>/dev/null || echo "BRANCH")

    echo "BLOCKED: Direct script call is not allowed" >&2
    echo "" >&2
    echo "Running 'python scripts/safe_worktree_remove.py' directly may use a stale" >&2
    echo "copy of the script from your worktree instead of the latest from main." >&2
    echo "" >&2
    echo "Use the proper command instead:" >&2
    echo "  make worktree-remove BRANCH=$BRANCH" >&2
    exit 2
fi

# Block direct calls to finish_pr.py (must use make finish)
# This ensures proper workflow and uses main's scripts
if echo "$COMMAND" | grep -qE '(^|&&|;|\|)\s*python[3]?\s+scripts/finish_pr\.py'; then
    BRANCH=$(echo "$COMMAND" | grep -oE '\-\-branch\s+\S+' | sed 's/--branch\s*//' || echo "BRANCH")
    PR_NUM=$(echo "$COMMAND" | grep -oE '\-\-pr\s+[0-9]+' | grep -oE '[0-9]+' || echo "N")

    echo "BLOCKED: Direct script call is not allowed" >&2
    echo "" >&2
    echo "Running 'python scripts/finish_pr.py' directly may use a stale" >&2
    echo "copy of the script from your worktree instead of the latest from main." >&2
    echo "" >&2
    echo "Use the proper command instead:" >&2
    echo "  make finish BRANCH=$BRANCH PR=$PR_NUM" >&2
    exit 2
fi

# Get the working directory from the tool input
CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

# Check if CWD is inside a worktree
if [[ "$CWD" == */worktrees/* ]]; then
    # Extract main directory and branch info for error messages
    MAIN_DIR=$(echo "$CWD" | sed 's|/worktrees/.*||')
    BRANCH=$(basename "$CWD")

    # Block ANY worktree deletion command from inside a worktree
    # This includes: make finish, make worktree-remove, safe_worktree_remove.py
    # Skip git commands (they can't delete worktrees - that's caught by block-worktree-remove.sh)
    # This avoids false positives from commit messages containing these words
    if ! echo "$COMMAND" | grep -qE '^git\s' && echo "$COMMAND" | grep -qE '(^|&&|;|\|)\s*(make\s+(finish|worktree-remove)|python.*safe_worktree_remove)'; then
        echo "BLOCKED: Cannot delete worktrees while inside a worktree!" >&2
        echo "" >&2
        echo "Your shell CWD is: $CWD" >&2
        echo "" >&2
        echo "If you delete this (or any) worktree, your shell will break." >&2
        echo "" >&2
        echo "FIRST, change your shell directory:" >&2
        echo "  cd $MAIN_DIR" >&2
        echo "" >&2
        echo "THEN run your command:" >&2
        echo "  make finish BRANCH=$BRANCH PR=N" >&2
        echo "" >&2
        echo "NOTE: 'cd /path/to/main && make finish' does NOT work!" >&2
        echo "      The cd must be a SEPARATE command to change your shell CWD." >&2
        exit 2
    fi

    # Block make merge from worktree (suggest finish from main)
    if echo "$COMMAND" | grep -qE '(^|&&|\|\||;)\s*make\s+merge(\s|$)'; then
        PR_NUM=$(echo "$COMMAND" | grep -oE 'PR=[0-9]+' | grep -oE '[0-9]+' || echo "N")

        echo "BLOCKED: Cannot run 'make merge' from inside a worktree" >&2
        echo "" >&2
        echo "Your shell CWD is: $CWD" >&2
        echo "" >&2
        echo "FIRST, change to main:" >&2
        echo "  cd $MAIN_DIR" >&2
        echo "" >&2
        echo "THEN use 'make finish' for the complete workflow:" >&2
        echo "  make finish BRANCH=$BRANCH PR=$PR_NUM" >&2
        exit 2
    fi
fi

exit 0
