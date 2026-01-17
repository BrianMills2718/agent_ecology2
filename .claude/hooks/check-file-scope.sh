#!/bin/bash
# File Scope Enforcement Hook for Claude Code
# Blocks Edit/Write operations to files not declared in the active plan's Files Affected section.
#
# Exit codes:
#   0 - Allow the operation
#   2 - Block the operation
#
# This hook enforces planning discipline by requiring CC to declare
# which files it will touch before editing them.

set -e

# Get the main repo root
MAIN_DIR=$(git rev-parse --git-common-dir 2>/dev/null | xargs dirname)
if [[ -z "$MAIN_DIR" ]]; then
    exit 0  # Not in a git repo, allow
fi

# Read tool input to get file path
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [[ -z "$FILE_PATH" ]]; then
    exit 0  # No file_path, allow
fi

# Allow writes to worktree-specific paths
if [[ "$FILE_PATH" == *"/worktrees/"* ]]; then
    # Extract the worktree-relative path
    WORKTREE_PATH=$(echo "$FILE_PATH" | sed 's|.*/worktrees/[^/]*/||')
else
    # Not in a worktree, use path relative to main
    WORKTREE_PATH=$(echo "$FILE_PATH" | sed "s|^$MAIN_DIR/||")
fi

# Allow coordination files without plan declaration
if [[ "$WORKTREE_PATH" == ".claude/"* ]] || \
   [[ "$WORKTREE_PATH" == *"CLAUDE.md" ]] || \
   [[ "$WORKTREE_PATH" == ".git/"* ]] || \
   [[ "$WORKTREE_PATH" == "docs/plans/"* ]]; then
    exit 0  # Coordination/plan files always allowed
fi

# Check if this is a trivial commit context
# (We can't know for sure, but we allow if no plan is active)
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "unknown")

# Skip check for main branch (reviews only, not implementation)
if [[ "$BRANCH" == "main" ]]; then
    exit 0
fi

# Try to get active plan number from branch name
PLAN_NUM=""
if [[ "$BRANCH" =~ ^plan-([0-9]+) ]]; then
    PLAN_NUM="${BASH_REMATCH[1]}"
fi

# If no plan number in branch, check claims
if [[ -z "$PLAN_NUM" ]]; then
    # No plan context - allow (might be trivial work)
    exit 0
fi

# Check if file is in plan's scope using parse_plan.py
SCRIPT_DIR="$MAIN_DIR/scripts"
if [[ ! -f "$SCRIPT_DIR/parse_plan.py" ]]; then
    # Parser not available - allow (graceful degradation)
    exit 0
fi

# Run the check
RESULT=$(python "$SCRIPT_DIR/parse_plan.py" --plan "$PLAN_NUM" --check-file "$WORKTREE_PATH" --json 2>/dev/null || echo '{"error": "parse_failed"}')

# Parse result
IN_SCOPE=$(echo "$RESULT" | jq -r '.in_scope // false')
ERROR=$(echo "$RESULT" | jq -r '.error // empty')

# Handle errors gracefully (allow on error)
if [[ -n "$ERROR" ]]; then
    if [[ "$ERROR" == "plan_not_found" ]]; then
        # Plan file doesn't exist - allow (might be new plan)
        exit 0
    fi
    # Other errors - allow (graceful degradation)
    exit 0
fi

# Check scope
if [[ "$IN_SCOPE" == "true" ]]; then
    exit 0  # File is in scope, allow
fi

# File not in scope - block with helpful message
echo "BLOCKED: File not in plan's declared scope" >&2
echo "" >&2
echo "Plan #$PLAN_NUM does not list this file in 'Files Affected':" >&2
echo "  $WORKTREE_PATH" >&2
echo "" >&2
echo "To fix, update your plan file:" >&2
echo "  docs/plans/${PLAN_NUM}_*.md" >&2
echo "" >&2
echo "Add to '## Files Affected' section:" >&2
echo "  - $WORKTREE_PATH (modify)" >&2
echo "  or" >&2
echo "  - $WORKTREE_PATH (create)" >&2
echo "" >&2
echo "This ensures all changes are planned and traceable." >&2

exit 2
