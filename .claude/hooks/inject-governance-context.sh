#!/bin/bash
# Inject governance context after Read tool completes (Plan #217)
#
# This hook provides governance context (ADRs, descriptions) for files
# that are governed according to relationships.yaml.
#
# Exit codes:
#   0 - Success (may output JSON with additionalContext)
#
# Output format (JSON on stdout at exit 0):
#   {
#     "hookSpecificOutput": {
#       "hookEventName": "PostToolUse",
#       "additionalContext": "Governance context here..."
#     }
#   }
#
# Configuration:
#   Controlled by hooks.inject_governance_context in meta-process.yaml
#   Default: true (enabled)

set -e

# Check if hook is enabled via config
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/check-hook-enabled.sh"
if ! is_hook_enabled "inject_governance_context"; then
    exit 0  # Hook disabled in config
fi

# Read tool input from stdin
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")

if [[ -z "$FILE_PATH" ]]; then
    exit 0  # No file path, nothing to do
fi

# Get the main repo root (absolute path)
MAIN_DIR=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [[ -z "$MAIN_DIR" ]]; then
    exit 0  # Not in a git repo
fi

# Normalize file path to be relative to repo root
REL_PATH="$FILE_PATH"
if [[ "$FILE_PATH" == "$MAIN_DIR/"* ]]; then
    REL_PATH="${FILE_PATH#$MAIN_DIR/}"
fi

# Handle worktree paths - extract the repo-relative path
# Case 1: Absolute path like /home/.../worktrees/branch-name/src/...
if [[ "$REL_PATH" == *"/worktrees/"* ]] || [[ "$REL_PATH" == *"_worktrees/"* ]]; then
    REL_PATH=$(echo "$REL_PATH" | sed 's|.*/[^/]*worktrees/[^/]*/||')
# Case 2: Relative path like worktrees/branch-name/src/...
elif [[ "$REL_PATH" == worktrees/* ]]; then
    REL_PATH=$(echo "$REL_PATH" | sed 's|^worktrees/[^/]*/||')
fi

# Run Python script to get governance context
# Check worktree first, then fall back to main
SCRIPT_PATH=""
WORKTREE_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || echo "")
if [[ -n "$WORKTREE_ROOT" && -f "$WORKTREE_ROOT/scripts/get_governance_context.py" ]]; then
    SCRIPT_PATH="$WORKTREE_ROOT/scripts/get_governance_context.py"
elif [[ -f "$MAIN_DIR/scripts/get_governance_context.py" ]]; then
    SCRIPT_PATH="$MAIN_DIR/scripts/get_governance_context.py"
fi

if [[ -z "$SCRIPT_PATH" ]]; then
    exit 0  # Script not available
fi

# Get context (script outputs JSON or empty)
# Run from the directory containing the script (for relationships.yaml access)
SCRIPT_DIR_PATH=$(dirname "$SCRIPT_PATH")
CONTEXT=$(cd "$(dirname "$SCRIPT_DIR_PATH")" && python "$SCRIPT_PATH" "$REL_PATH" 2>/dev/null || echo "")

if [[ -z "$CONTEXT" ]] || [[ "$CONTEXT" == "null" ]] || [[ "$CONTEXT" == "{}" ]]; then
    exit 0  # No governance context for this file
fi

# Check visibility config — should we tag for user surfacing?
VISIBILITY=$(cd "$(dirname "$SCRIPT_DIR_PATH")" && python scripts/meta_config.py --get visibility.context_surfacing 2>/dev/null || echo "both")

if [[ "$VISIBILITY" == "automatic" || "$VISIBILITY" == "both" ]]; then
    # Wrap context in SHOW_USER tags so Claude surfaces it to the user
    CONTEXT_STR=$(echo "$CONTEXT" | jq -r '.' 2>/dev/null || echo "$CONTEXT")
    TAGGED=$'[SHOW_USER]\n'"$CONTEXT_STR"$'\n[/SHOW_USER]'
    TAGGED_ESCAPED=$(echo "$TAGGED" | jq -Rs .)
    cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": $TAGGED_ESCAPED
  }
}
EOF
else
    # Claude sees it but user doesn't
    cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": $CONTEXT
  }
}
EOF
fi

exit 0
