#!/bin/bash
# Worktree Enforcement Hook for Claude Code
# Blocks Edit/Write operations in the main directory.
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

# Check if file path is inside a worktrees directory (allow writes to worktrees)
if [[ "$FILE_PATH" == *"/worktrees/"* ]]; then
    exit 0  # Writing to a worktree, allow
fi

# Check if we're in a worktree (main has .git directory, worktree has .git file)
if [[ -f "$MAIN_DIR/.git" ]]; then
    exit 0  # We're in a worktree, allow all writes
fi

# We're in main. Check if file is allowed.

# Allow coordination files in main
BASENAME=$(basename "$FILE_PATH")
if [[ "$FILE_PATH" == *"/.claude/"* ]] || \
   [[ "$BASENAME" == "CLAUDE.md" ]] || \
   [[ "$FILE_PATH" == *"/.git/"* ]]; then
    exit 0  # Coordination files allowed
fi

# Check if file is in main directory
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
