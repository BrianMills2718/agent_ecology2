#!/bin/bash
# Refresh session marker on Edit/Write operations
# Plan #52: Worktree Session Tracking
#
# This hook runs AFTER Edit/Write operations to update the session marker,
# indicating that a Claude session is actively using this worktree.
#
# IMPORTANT: With "run from main" workflow, CC runs from main but edits
# files via worktree paths. We must check the FILE_PATH, not PWD.

# Read tool input from stdin (PostToolUse hooks receive this)
INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty' 2>/dev/null)

# If no file path in input, nothing to do
if [[ -z "$FILE_PATH" ]]; then
    exit 0
fi

# Check if the file is in a worktree (either by path or PWD)
WORKTREE_ROOT=""

# Method 1: Check if file path contains /worktrees/
if [[ "$FILE_PATH" == *"/worktrees/"* ]]; then
    # Extract worktree root from file path
    WORKTREE_ROOT=$(echo "$FILE_PATH" | sed 's|\(.*worktrees/[^/]*\).*|\1|')
fi

# Method 2: Check if PWD is in a worktree (legacy support)
if [[ -z "$WORKTREE_ROOT" ]] && [[ "$PWD" == *"/worktrees/"* ]]; then
    WORKTREE_ROOT=$(echo "$PWD" | sed 's|\(.*worktrees/[^/]*\).*|\1|')
fi

# Update the session marker if we found a worktree
if [[ -n "$WORKTREE_ROOT" ]] && [[ -d "$WORKTREE_ROOT" ]]; then
    echo "$(date -Iseconds)" > "$WORKTREE_ROOT/.claude_session"
fi

# Always exit 0 - we don't want to block edits if marker refresh fails
exit 0
