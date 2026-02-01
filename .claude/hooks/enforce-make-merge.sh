#!/bin/bash
# Block direct GitHub CLI merge and enforce proper merge workflow (Plan #115)
# Also blocks direct script calls that bypass make targets
#
# Rules:
# 1. No direct GitHub merge CLI - must use make finish
# 2. No direct python scripts/safe_worktree_remove.py - must use make worktree-remove
# 3. No direct python scripts/finish_pr.py - must use make finish
# 4. No direct python scripts/merge_pr.py - must use make finish
#
# NOTE: We no longer block commands from inside worktrees. Claude Code
# handles CWD deletion gracefully, and blocking caused worse outcomes
# by forcing CC to find bypasses that broke the shell.
#
# Exit codes:
#   0 - Allow the operation
#   2 - Block the operation
#
# Configuration:
#   Controlled by hooks.enforce_workflow in meta-process.yaml

set -e

# Check if hook is enabled via config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/check-hook-enabled.sh"
if ! is_hook_enabled "enforce_workflow"; then
    exit 0  # Hook disabled in config
fi

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
    echo "This bypasses worktree cleanup and claim release." >&2
    echo "" >&2
    echo "Use the proper command instead:" >&2
    echo "  make finish BRANCH=<branch> PR=$PR_NUM" >&2
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
# Pattern matches any path ending in finish_pr.py (catches absolute paths too)
if echo "$COMMAND" | grep -qE '(^|&&|;|\|)\s*python[3]?\s+[^ ]*finish_pr\.py'; then
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

# Block direct calls to merge_pr.py (must use make merge or make finish)
# This script cleans up worktrees after merge, which can break shell CWD
# Also ensures we use main's version of the script, not a stale worktree copy
# Pattern matches any path ending in merge_pr.py (catches absolute paths too)
if echo "$COMMAND" | grep -qE '(^|&&|;|\|)\s*python[3]?\s+[^ ]*merge_pr\.py'; then
    PR_NUM=$(echo "$COMMAND" | grep -oE '[0-9]+' | head -1 || echo "N")

    echo "BLOCKED: Direct script call is not allowed" >&2
    echo "" >&2
    echo "Running 'python scripts/merge_pr.py' directly may:" >&2
    echo "  - Use a stale copy from your worktree instead of main" >&2
    echo "  - Break your shell if CWD is in a worktree being cleaned up" >&2
    echo "" >&2
    echo "Use the proper command instead:" >&2
    echo "  make finish BRANCH=<branch> PR=$PR_NUM" >&2
    exit 2
fi

exit 0
