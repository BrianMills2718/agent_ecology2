#!/bin/bash
# Inject context BEFORE Edit tool runs (Plan #288)
#
# This hook provides relevant context from GLOSSARY, CONCEPTUAL_MODEL, ADRs, etc.
# when editing source files. It extracts terms from the file being edited and
# shows warnings for deprecated/forbidden terms.
#
# Exit codes:
#   0 - Success (with additionalContext)
#
# Output format (JSON on stdout):
#   {
#     "hookSpecificOutput": {
#       "hookEventName": "PreToolUse",
#       "additionalContext": "Context here..."
#     }
#   }

set -e

# Read tool input from stdin
INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")

# Only process Edit tool
if [[ "$TOOL_NAME" != "Edit" ]]; then
    exit 0
fi

if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Only process Python source files
if [[ "$FILE_PATH" != *.py ]]; then
    exit 0
fi

# Only process src/ files (not tests, scripts, etc.)
if [[ "$FILE_PATH" != *"/src/"* ]] && [[ "$FILE_PATH" != "src/"* ]]; then
    exit 0
fi

# Get the repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Go up from .claude/hooks to repo root
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Find the context extraction script
EXTRACT_SCRIPT=""
if [[ -f "$REPO_ROOT/scripts/extract_relevant_context.py" ]]; then
    EXTRACT_SCRIPT="$REPO_ROOT/scripts/extract_relevant_context.py"
fi

if [[ -z "$EXTRACT_SCRIPT" ]]; then
    exit 0  # Script not available
fi

# Normalize file path for the script
# Strip worktree prefix if present
REL_PATH="$FILE_PATH"
if [[ "$REL_PATH" == *"/worktrees/"* ]]; then
    REL_PATH=$(echo "$REL_PATH" | sed 's|.*/worktrees/[^/]*/||')
elif [[ "$REL_PATH" == "worktrees/"* ]]; then
    REL_PATH=$(echo "$REL_PATH" | sed 's|^worktrees/[^/]*/||')
fi

# Run the extraction script
CONTEXT=$(cd "$REPO_ROOT" && python "$EXTRACT_SCRIPT" "$REL_PATH" --format hook 2>/dev/null || echo "")

if [[ -z "$CONTEXT" ]]; then
    exit 0  # No context extracted
fi

# Check visibility config
VISIBILITY=$(cd "$REPO_ROOT" && python scripts/meta_config.py --get visibility.context_surfacing 2>/dev/null || echo "both")
if [[ "$VISIBILITY" == "automatic" || "$VISIBILITY" == "both" ]]; then
    TAGGED=$'[SHOW_USER]\n'"$CONTEXT"$'\n[/SHOW_USER]'
    CONTEXT_ESCAPED=$(echo "$TAGGED" | jq -Rs .)
else
    CONTEXT_ESCAPED=$(echo "$CONTEXT" | jq -Rs .)
fi

# Output JSON with additionalContext
cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PreToolUse",
    "additionalContext": $CONTEXT_ESCAPED
  }
}
EOF

exit 0
