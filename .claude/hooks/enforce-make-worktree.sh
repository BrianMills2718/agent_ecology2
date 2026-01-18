#!/bin/bash
# Block direct `git worktree add` commands that bypass claiming
# Forces use of `make worktree BRANCH=...` which claims work automatically
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

# Check if command contains `git worktree add`
if echo "$COMMAND" | grep -qE 'git\s+worktree\s+add'; then
    # Try to extract branch name for helpful message
    BRANCH=$(echo "$COMMAND" | grep -oE 'worktree\s+add\s+\S+\s+(\S+)' | awk '{print $NF}' || echo "BRANCH")

    echo "BLOCKED: Direct 'git worktree add' is not allowed" >&2
    echo "" >&2
    echo "This bypasses work claiming - other CC instances won't know you're working here." >&2
    echo "" >&2
    echo "Use the proper command instead:" >&2
    echo "  make worktree BRANCH=$BRANCH" >&2
    echo "" >&2
    echo "This will:" >&2
    echo "  1. Prompt for task description and plan number" >&2
    echo "  2. Claim the work (visible to other instances)" >&2
    echo "  3. Create the worktree" >&2
    exit 2
fi

exit 0
