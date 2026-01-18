#!/bin/bash
# Refresh session marker on Edit/Write operations
# Plan #52: Worktree Session Tracking
#
# This hook runs before Edit/Write operations to update the session marker,
# indicating that a Claude session is actively using this worktree.

# Only refresh if we're in a worktree (not main repo)
if [[ "$PWD" == *"/worktrees/"* ]]; then
    # Extract worktree root (assumes standard worktrees/<branch> structure)
    WORKTREE_ROOT=$(echo "$PWD" | sed 's|\(.*worktrees/[^/]*\).*|\1|')

    if [ -d "$WORKTREE_ROOT" ]; then
        echo "$(date -Iseconds)" > "$WORKTREE_ROOT/.claude_session"
    fi
fi

# Always exit 0 - we don't want to block edits if marker refresh fails
exit 0
