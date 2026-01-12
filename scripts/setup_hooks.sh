#!/bin/bash
# Configure git to use tracked hooks directory
# Run this once after cloning the repo

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/hooks"

echo "Configuring git hooks..."

# Verify hooks directory exists
if [ ! -d "$HOOKS_DIR" ]; then
    echo "ERROR: hooks/ directory not found"
    echo "This should be tracked in the repo"
    exit 1
fi

# Make hooks executable
chmod +x "$HOOKS_DIR"/*

# Configure git to use tracked hooks directory
git config core.hooksPath hooks

echo "Git hooks configured successfully!"
echo ""
echo "Using tracked hooks from: $HOOKS_DIR"
echo "  - commit-msg: Enforces plan references"
echo "  - pre-commit: Doc-coupling and mypy checks"
echo ""
echo "To bypass (not recommended): git commit --no-verify"
