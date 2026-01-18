#!/bin/bash
# Block direct `gh pr merge` commands that bypass worktree auto-cleanup
# Forces use of `make merge PR=N` which handles cleanup automatically
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

exit 0
