#!/bin/bash
# Worktree Enforcement Hook for Claude Code
# Blocks Edit/Write operations in:
#   1. The main directory (must use worktrees)
#   2. Worktrees without an active claim (must claim before editing)
#
# Exit codes:
#   0 - Allow the operation
#   2 - Block the operation

set -e

# Detect main directory dynamically (works on any machine)
MAIN_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
if [[ -z "$MAIN_DIR" ]]; then
    exit 0  # Not in a git repo, allow
fi

# Read tool input first to get file path
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
    exit 0  # No file_path, allow
fi

# Allow coordination files everywhere
BASENAME=$(basename "$FILE_PATH")
if [[ "$FILE_PATH" == *"/.claude/"* ]] || \
   [[ "$BASENAME" == "CLAUDE.md" ]] || \
   [[ "$FILE_PATH" == *"/.git/"* ]] || \
   [[ "$BASENAME" == ".claude_session" ]]; then
    exit 0  # Coordination files allowed
fi

# Get the main repo root (not the worktree's root)
MAIN_REPO_ROOT=$(git worktree list | head -1 | awk '{print $1}')

# Check if we're in a worktree (main has .git directory, worktree has .git file)
if [[ -f "$MAIN_DIR/.git" ]]; then
    # We're in a worktree - check for active claim
    BRANCH=$(git branch --show-current 2>/dev/null)

    if [[ -z "$BRANCH" ]]; then
        exit 0  # Detached HEAD, allow (edge case)
    fi

    # Check if this branch has a claim
    CLAIMS_FILE="$MAIN_REPO_ROOT/.claude/active-work.yaml"
    HAS_CLAIM=false

    if [[ -f "$CLAIMS_FILE" ]]; then
        # Look for cc_id matching the branch name
        if grep -q "cc_id: $BRANCH" "$CLAIMS_FILE" 2>/dev/null; then
            HAS_CLAIM=true
        fi
    fi

    if [[ "$HAS_CLAIM" == "true" ]]; then
        exit 0  # Has claim, allow edit
    else
        echo "BLOCKED: Worktree has no active claim" >&2
        echo "" >&2
        echo "Branch '$BRANCH' has no claim in .claude/active-work.yaml" >&2
        echo "" >&2
        echo "Create a claim first:" >&2
        echo "  python scripts/check_claims.py --claim --task 'description' --id $BRANCH" >&2
        echo "" >&2
        echo "Or if this is abandoned work, remove the worktree:" >&2
        echo "  make worktree-remove BRANCH=$BRANCH" >&2
        echo "" >&2
        echo "File: $FILE_PATH" >&2
        exit 2
    fi
fi

# We're in main directory - check if file is in main
if [[ "$FILE_PATH" == "$MAIN_DIR"/* ]]; then
    echo "BLOCKED: Cannot edit files in main directory" >&2
    echo "" >&2
    echo "Create a worktree first:" >&2
    echo "  make worktree BRANCH=plan-NN-description" >&2
    echo "" >&2
    echo "File: $FILE_PATH" >&2
    exit 2
fi

exit 0
