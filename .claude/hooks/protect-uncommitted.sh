#!/bin/bash
# Protect Uncommitted Changes Hook for Claude Code
# Blocks destructive git commands when uncommitted changes exist in main.
#
# Exit codes:
#   0 - Allow the operation
#   2 - Block the operation

set -e

# Read the tool input
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [[ -z "$COMMAND" ]]; then
    exit 0  # No command, allow
fi

# Only check destructive git commands
if ! echo "$COMMAND" | grep -qE 'git\s+(checkout|reset|clean|stash)'; then
    exit 0  # Not a destructive git command, allow
fi

# Get main directory
MAIN_DIR=$(git rev-parse --show-toplevel 2>/dev/null)
if [[ -z "$MAIN_DIR" ]]; then
    exit 0  # Not in a git repo, allow
fi

# Check if we're in main (not a worktree)
# Worktrees have .git as a file, main has .git as a directory
if [[ -f "$MAIN_DIR/.git" ]]; then
    exit 0  # We're in a worktree, allow (worktrees are isolated)
fi

# We're in main. Check for uncommitted changes.
cd "$MAIN_DIR"

# Check for any uncommitted changes (staged, unstaged, or untracked)
if ! git diff --quiet 2>/dev/null || ! git diff --cached --quiet 2>/dev/null; then
    # There are uncommitted changes - check if this command would affect them

    # git checkout <file> or git checkout . - dangerous
    if echo "$COMMAND" | grep -qE 'git\s+checkout\s+(\.|[^-])'; then
        echo "BLOCKED: Uncommitted changes in main would be lost" >&2
        echo "" >&2
        echo "You have uncommitted changes. This command would discard them:" >&2
        echo "  $COMMAND" >&2
        echo "" >&2
        echo "Options:" >&2
        echo "  1. Commit your changes first: git add . && git commit -m 'WIP'" >&2
        echo "  2. Stash your changes: git stash" >&2
        echo "  3. Move to a worktree for safety" >&2
        exit 2
    fi

    # git reset --hard - always dangerous with uncommitted changes
    if echo "$COMMAND" | grep -qE 'git\s+reset\s+--hard'; then
        echo "BLOCKED: Uncommitted changes in main would be lost" >&2
        echo "" >&2
        echo "You have uncommitted changes. This command would discard them:" >&2
        echo "  $COMMAND" >&2
        echo "" >&2
        echo "Options:" >&2
        echo "  1. Commit your changes first" >&2
        echo "  2. Stash your changes: git stash" >&2
        echo "  3. Use git reset (without --hard) to keep changes" >&2
        exit 2
    fi

    # git clean -f - removes untracked files
    if echo "$COMMAND" | grep -qE 'git\s+clean\s+-[fd]'; then
        echo "BLOCKED: Untracked files in main would be deleted" >&2
        echo "" >&2
        echo "Command: $COMMAND" >&2
        echo "" >&2
        echo "Options:" >&2
        echo "  1. Add files to .gitignore if they shouldn't be tracked" >&2
        echo "  2. Commit or stash your changes first" >&2
        exit 2
    fi
fi

exit 0
