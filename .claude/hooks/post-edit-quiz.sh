#!/bin/bash
# Post-edit quiz — surfaces understanding questions after editing src/ files.
# PostToolUse/Edit hook — shows constraint quiz after successful edits.
#
# This is advisory (exit 0) — it doesn't block, just prompts engagement.
#
# Only triggers for src/ files with governance entries.

set -e

INPUT=$(cat)
TOOL_NAME=$(echo "$INPUT" | jq -r '.tool_name // empty' 2>/dev/null || echo "")
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null || echo "")

# Only fire after Edit and Write
if [[ "$TOOL_NAME" != "Edit" && "$TOOL_NAME" != "Write" ]]; then
    exit 0
fi

if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Only for src/ files
if [[ "$FILE_PATH" != *"/src/"* ]] && [[ "$FILE_PATH" != "src/"* ]]; then
    exit 0
fi

# Bypass
if [[ "${SKIP_QUIZ:-}" == "1" ]]; then
    exit 0
fi

# Get repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Normalize path
REL_PATH="$FILE_PATH"
if [[ "$FILE_PATH" == "$REPO_ROOT/"* ]]; then
    REL_PATH="${FILE_PATH#$REPO_ROOT/}"
fi
if [[ "$REL_PATH" == worktrees/* ]]; then
    REL_PATH=$(echo "$REL_PATH" | sed 's|^worktrees/[^/]*/||')
fi

# Find quiz script
QUIZ_SCRIPT="$REPO_ROOT/scripts/generate_quiz.py"
if [[ ! -f "$QUIZ_SCRIPT" ]]; then
    exit 0
fi

# Get trivial threshold from config (0 = disabled)
THRESHOLD=$(cd "$REPO_ROOT" && python scripts/meta_config.py --get quiz.trivial_threshold 2>/dev/null || echo "0")
THRESHOLD_FLAG=""
if [[ "$THRESHOLD" != "0" ]] && [[ "$THRESHOLD" != "None" ]] && [[ -n "$THRESHOLD" ]]; then
    THRESHOLD_FLAG="--trivial-threshold $THRESHOLD"
fi

# Generate quiz (JSON mode for structured output)
set +e
RESULT=$(cd "$REPO_ROOT" && python "$QUIZ_SCRIPT" "$REL_PATH" --json $THRESHOLD_FLAG 2>/dev/null)
QUIZ_EXIT=$?
set -e

if [[ $QUIZ_EXIT -ne 0 ]] || [[ -z "$RESULT" ]] || [[ "$RESULT" == "[]" ]]; then
    exit 0
fi

# Extract just the questions as readable text
QUIZ_TEXT=$(cd "$REPO_ROOT" && python "$QUIZ_SCRIPT" "$REL_PATH" $THRESHOLD_FLAG 2>/dev/null)

if [[ -z "$QUIZ_TEXT" ]]; then
    exit 0
fi

# Check visibility config for quiz mode
QUIZ_VISIBILITY=$(cd "$REPO_ROOT" && python scripts/meta_config.py --get visibility.quiz_mode 2>/dev/null || echo "both")
if [[ "$QUIZ_VISIBILITY" == "automatic" || "$QUIZ_VISIBILITY" == "both" ]]; then
    TAGGED=$'[SHOW_USER]\n'"$QUIZ_TEXT"$'\n[/SHOW_USER]'
    QUIZ_ESCAPED=$(echo "$TAGGED" | jq -Rs .)
else
    QUIZ_ESCAPED=$(echo "$QUIZ_TEXT" | jq -Rs .)
fi

cat << EOF
{
  "hookSpecificOutput": {
    "hookEventName": "PostToolUse",
    "additionalContext": $QUIZ_ESCAPED
  }
}
EOF

exit 0
