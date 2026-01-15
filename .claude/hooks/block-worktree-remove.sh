#!/bin/bash
# Block direct `git worktree` commands that bypass safety checks
# Forces use of `make worktree` (creates claim) and `make worktree-remove` (checks uncommitted)
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
    echo "BLOCKED: Direct 'git worktree add' is not allowed" >&2
    echo "" >&2
    echo "This bypasses the claim system - other instances won't know you're working on this." >&2
    echo "" >&2
    echo "Use the proper command instead:" >&2
    echo "  make worktree BRANCH=plan-NN-description" >&2
    echo "" >&2
    echo "This will:" >&2
    echo "  1. Prompt for task description and plan number" >&2
    echo "  2. Create a claim so other instances see your work" >&2
    echo "  3. Create the worktree" >&2
    exit 2
fi

# Check if command contains `git worktree remove`
if echo "$COMMAND" | grep -qE 'git\s+worktree\s+remove'; then
    echo "BLOCKED: Direct 'git worktree remove' is not allowed" >&2
    echo "" >&2
    echo "This command can break your shell session and lose uncommitted work." >&2
    echo "" >&2
    echo "Use the safe removal command instead:" >&2
    echo "  make worktree-remove BRANCH=<branch-name>" >&2
    echo "" >&2
    echo "Or if you must remove manually:" >&2
    echo "  python scripts/safe_worktree_remove.py <worktree-path>" >&2
    exit 2
fi

exit 0
