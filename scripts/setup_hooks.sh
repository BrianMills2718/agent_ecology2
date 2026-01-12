#!/bin/bash
# Install git hooks for agent_ecology
# Run this once after cloning the repo

set -e

REPO_ROOT=$(git rev-parse --show-toplevel)
HOOKS_DIR="$REPO_ROOT/.git/hooks"

echo "Installing git hooks..."

# Create pre-commit hook
cat > "$HOOKS_DIR/pre-commit" << 'EOF'
#!/bin/bash
# Pre-commit hook for agent_ecology
# Catches issues before they reach CI

set -e

echo "Running pre-commit checks..."

# Get the repo root
REPO_ROOT=$(git rev-parse --show-toplevel)
cd "$REPO_ROOT"

# Get staged Python files
STAGED_PY=$(git diff --cached --name-only --diff-filter=ACM | grep '\.py$' || true)

# 1. Doc-coupling check (strict violations only)
echo "Checking doc-code coupling..."
if ! python scripts/check_doc_coupling.py --strict 2>/dev/null; then
    echo ""
    echo "ERROR: Doc-coupling violation detected!"
    echo "Run 'python scripts/check_doc_coupling.py --suggest' to see which docs to update."
    echo ""
    exit 1
fi

# 2. Mypy on changed src/ files
STAGED_SRC=$(echo "$STAGED_PY" | grep '^src/' || true)
if [ -n "$STAGED_SRC" ]; then
    echo "Running mypy on changed files..."
    MYPY_FILES=""
    for f in $STAGED_SRC; do
        case "$f" in
            src/config.py|src/world/*.py|src/agents/*.py)
                MYPY_FILES="$MYPY_FILES $f"
                ;;
        esac
    done

    if [ -n "$MYPY_FILES" ]; then
        if ! python -m mypy --strict --ignore-missing-imports $MYPY_FILES 2>/dev/null; then
            echo ""
            echo "ERROR: mypy type check failed!"
            echo ""
            exit 1
        fi
    fi
fi

# 3. Validate coupling config
echo "Validating coupling config..."
if ! python scripts/check_doc_coupling.py --validate-config 2>/dev/null; then
    echo ""
    echo "ERROR: Invalid doc-coupling config"
    echo ""
    exit 1
fi

echo "Pre-commit checks passed!"
EOF

chmod +x "$HOOKS_DIR/pre-commit"

# Create commit-msg hook (enforces plan references)
cat > "$HOOKS_DIR/commit-msg" << 'EOF'
#!/bin/bash
# Commit-msg hook for agent_ecology
# Enforces that all commits reference a plan

COMMIT_MSG_FILE="$1"
COMMIT_MSG=$(cat "$COMMIT_MSG_FILE")
FIRST_LINE=$(head -n1 "$COMMIT_MSG_FILE")

# Allow merge commits
if [[ "$FIRST_LINE" =~ ^Merge ]]; then
    exit 0
fi

# Allow fixup/squash commits
if [[ "$FIRST_LINE" =~ ^(fixup!|squash!) ]]; then
    exit 0
fi

# Allow amend commits (usually fixing previous)
if [[ "$FIRST_LINE" =~ ^(amend|Amend) ]]; then
    exit 0
fi

# Check for plan reference: [Plan #N] or [Unplanned]
if [[ "$FIRST_LINE" =~ ^\[Plan\ \#[0-9]+\] ]]; then
    exit 0
fi

if [[ "$FIRST_LINE" =~ ^\[Unplanned\] ]]; then
    echo ""
    echo "WARNING: Unplanned work detected."
    echo "Before merging, create a plan entry in docs/plans/"
    echo ""
    exit 0
fi

# Reject commits without plan reference
echo ""
echo "ERROR: Commit message must reference a plan!"
echo ""
echo "Format: [Plan #N] Short description"
echo "   e.g. [Plan #3] Implement docker isolation"
echo ""
echo "For unplanned work: [Unplanned] Short description"
echo "   (You must create a plan entry before merging)"
echo ""
echo "Your message: $FIRST_LINE"
echo ""
exit 1
EOF

chmod +x "$HOOKS_DIR/commit-msg"

echo "Git hooks installed successfully!"
echo ""
echo "Hooks installed:"
echo "  - pre-commit: doc-coupling, mypy, config validation"
echo "  - commit-msg: plan reference enforcement"
echo ""
echo "To bypass (not recommended): git commit --no-verify"
