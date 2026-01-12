#!/bin/bash
# Worktree Enforcement Hook
# Blocks Edit/Write operations in the main directory to prevent conflicts
# between multiple Claude Code instances.
#
# Exit codes:
#   0 - Allow the operation
#   2 - Block the operation (Claude Code will show error message)

set -e

# Main directory path (update for your project)
MAIN_DIR="/home/azureuser/brian_misc/agent_ecology"

# Read tool input from stdin (JSON with tool_input field)
INPUT=$(cat)

# Extract file_path from the tool input
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

# If no file_path, allow (might be a different tool structure)
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Allow coordination files even in main directory
# These files are used for multi-CC coordination and must be editable
BASENAME=$(basename "$FILE_PATH")
if [[ "$FILE_PATH" == *"/.claude/"* ]] || \
   [[ "$BASENAME" == "CLAUDE.md" ]]; then
    exit 0  # Coordination files are allowed in main
fi

# Get directory of the file being edited
FILE_DIR=$(dirname "$FILE_PATH")

# Check if file is in the main directory (not a worktree)
if [[ "$FILE_PATH" == "$MAIN_DIR"/* ]] || [[ "$FILE_PATH" == "$MAIN_DIR" ]]; then
    echo "BLOCKED: Cannot edit files in main directory ($MAIN_DIR)" >&2
    echo "" >&2
    echo "You're in the main directory. Create a worktree first:" >&2
    echo "  make worktree BRANCH=plan-NN-description" >&2
    echo "" >&2
    echo "Or use an existing worktree:" >&2
    echo "  make worktree-list" >&2
    exit 2  # Exit code 2 = block the tool call
fi

exit 0  # Allow
