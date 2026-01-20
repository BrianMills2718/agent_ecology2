#!/bin/bash
# Block direct `gh pr merge` and enforce proper merge workflow (Plan #115)
# - Blocks direct `gh pr merge` (must use make merge/finish)
# - Blocks merge commands from inside worktrees (must run from main)
# - Recommends `make finish` for complete workflow
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

# Check if command contains `gh pr merge` (with various patterns)
if echo "$COMMAND" | grep -qE 'gh\s+pr\s+merge'; then
    # Extract PR number if present
    PR_NUM=$(echo "$COMMAND" | grep -oE 'merge\s+[0-9]+' | grep -oE '[0-9]+' || echo "N")

    echo "BLOCKED: Direct 'gh pr merge' is not allowed" >&2
    echo "" >&2
    echo "This bypasses worktree auto-cleanup - orphan worktrees will accumulate." >&2
    echo "" >&2
    echo "Use the proper command instead:" >&2
    echo "  make merge PR=$PR_NUM" >&2
    echo "" >&2
    echo "This will:" >&2
    echo "  1. Merge the PR via GitHub CLI" >&2
    echo "  2. Auto-cleanup the local worktree for the merged branch" >&2
    echo "  3. Pull latest main" >&2
    exit 2
fi

# Check if running `make merge` or `make finish` from inside a worktree
# Only match at command start or after shell operators (&&, ||, ;)
# This avoids false positives from text containing these words
if echo "$COMMAND" | grep -qE '(^|&&|\|\||;)\s*make\s+(merge|finish)(\s|$)'; then
    # Get the working directory from the tool input
    CWD=$(echo "$INPUT" | jq -r '.cwd // empty')

    # Check if CWD is inside a worktree
    if [[ "$CWD" == */worktrees/* ]]; then
        # Allow if command includes cd to main directory first
        # Pattern: cd /path/to/main && make merge/finish
        MAIN_DIR=$(echo "$CWD" | sed 's|/worktrees/.*||')
        if echo "$COMMAND" | grep -qE "cd\s+['\"]?${MAIN_DIR}['\"]?\s*&&"; then
            # Command includes cd to main - allow it
            exit 0
        fi

        # Extract branch name from worktree path
        BRANCH=$(basename "$CWD")
        # Extract PR number if present in command
        PR_NUM=$(echo "$COMMAND" | grep -oE 'PR=[0-9]+' | grep -oE '[0-9]+' || echo "N")

        echo "BLOCKED: Cannot run merge/finish from inside a worktree" >&2
        echo "" >&2
        echo "You are in: $CWD" >&2
        echo "" >&2
        echo "Run from main directory instead:" >&2
        echo "  cd $MAIN_DIR && make finish BRANCH=$BRANCH PR=$PR_NUM" >&2
        echo "" >&2
        echo "This ensures proper cleanup of the worktree you're currently in." >&2
        exit 2
    fi

    # When running make merge from main, suggest make finish instead
    if echo "$COMMAND" | grep -qE '(^|&&|\|\||;)\s*make\s+merge(\s|$)'; then
        # Extract PR number if present
        PR_NUM=$(echo "$COMMAND" | grep -oE 'PR=[0-9]+' | grep -oE '[0-9]+' || echo "N")
        BRANCH_ARG=$(echo "$COMMAND" | grep -oE 'BRANCH=[^ ]+' | cut -d= -f2 || echo "")

        echo "SUGGESTION: Consider using 'make finish' instead of 'make merge'" >&2
        echo "" >&2
        echo "  make finish BRANCH=${BRANCH_ARG:-<branch>} PR=$PR_NUM" >&2
        echo "" >&2
        echo "make finish provides the complete workflow:" >&2
        echo "  1. Merge the PR" >&2
        echo "  2. Release the claim" >&2
        echo "  3. Delete the worktree" >&2
        echo "  4. Pull latest main" >&2
        echo "" >&2
        # Allow but warn (exit 0)
    fi
fi

exit 0
