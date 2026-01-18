#!/bin/bash
# Block `git checkout -b` in main worktree - forces proper worktree workflow
# Creating branches in main leads to conflicts when multiple CC instances work there
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

# Check if command creates a new branch
if echo "$COMMAND" | grep -qE 'git\s+(checkout\s+-b|switch\s+-c|branch\s+[^-])'; then
    # Check if we're in the main worktree (not a worktree subdirectory)
    CURRENT_DIR=$(pwd)

    # Get the main git directory
    GIT_TOPLEVEL=$(git rev-parse --show-toplevel 2>/dev/null || echo "")

    if [[ -z "$GIT_TOPLEVEL" ]]; then
        exit 0  # Not in a git repo, allow
    fi

    # Check if this is a worktree by looking for .git file (worktrees have .git file, main has .git dir)
    if [[ -d "$GIT_TOPLEVEL/.git" ]]; then
        # This is the main repo (has .git directory), not a worktree
        # Extract branch name for helpful message
        BRANCH=$(echo "$COMMAND" | grep -oE '(checkout\s+-b|switch\s+-c|branch)\s+(\S+)' | awk '{print $NF}' || echo "BRANCH")

        echo "BLOCKED: Creating branches in main worktree is not allowed" >&2
        echo "" >&2
        echo "Multiple CC instances share the main directory. Creating branches here" >&2
        echo "leads to conflicts and lost work." >&2
        echo "" >&2
        echo "Use the proper command instead:" >&2
        echo "  make worktree BRANCH=$BRANCH" >&2
        echo "" >&2
        echo "This creates an isolated worktree where you can safely work." >&2
        exit 2
    fi

    # We're in a worktree (.git is a file), allow branch operations
fi

exit 0
