#!/bin/bash
# Get the repository root directory.
# Used by hooks and scripts for portable path references.
#
# Usage:
#   source scripts/repo_root.sh
#   echo $REPO_ROOT
#
# Or in a script:
#   REPO_ROOT=$(bash scripts/repo_root.sh)

# Method 1: Git-based detection (most reliable)
if command -v git &> /dev/null; then
    REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null)
    if [ -n "$REPO_ROOT" ]; then
        echo "$REPO_ROOT"
        exit 0
    fi
fi

# Method 2: Script location based
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Verify it looks like our repo
if [ -f "$REPO_ROOT/meta-process.yaml" ] || [ -f "$REPO_ROOT/CLAUDE.md" ]; then
    echo "$REPO_ROOT"
    exit 0
fi

# Method 3: Walk up from current directory
CURRENT="$(pwd)"
while [ "$CURRENT" != "/" ]; do
    if [ -f "$CURRENT/meta-process.yaml" ] || [ -f "$CURRENT/CLAUDE.md" ]; then
        echo "$CURRENT"
        exit 0
    fi
    CURRENT="$(dirname "$CURRENT")"
done

# Fallback: error
echo "ERROR: Could not determine repository root" >&2
exit 1
