#!/bin/bash
# Meta-Process Installation Script
# Usage: ./install.sh /path/to/target/project [--minimal|--full]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_DIR="${1:-.}"
MODE="${2:---minimal}"

if [[ "$TARGET_DIR" == "-h" || "$TARGET_DIR" == "--help" ]]; then
    echo "Usage: $0 /path/to/project [--minimal|--full]"
    echo ""
    echo "Modes:"
    echo "  --minimal  Install core patterns only (plans, claims, worktrees)"
    echo "  --full     Install all patterns including acceptance gates"
    echo ""
    echo "After installation, edit meta-process.yaml to configure."
    exit 0
fi

# Resolve target directory
TARGET_DIR="$(cd "$TARGET_DIR" && pwd)"

echo -e "${GREEN}Installing meta-process to: $TARGET_DIR${NC}"
echo -e "Mode: $MODE"
echo ""

# Check if git repo
if [[ ! -d "$TARGET_DIR/.git" ]]; then
    echo -e "${RED}Error: $TARGET_DIR is not a git repository${NC}"
    exit 1
fi

# Create directories
echo "Creating directories..."
mkdir -p "$TARGET_DIR/docs/plans"
mkdir -p "$TARGET_DIR/scripts/meta"
mkdir -p "$TARGET_DIR/hooks"
mkdir -p "$TARGET_DIR/.claude/hooks"

if [[ "$MODE" == "--full" ]]; then
    mkdir -p "$TARGET_DIR/acceptance_gates"
    mkdir -p "$TARGET_DIR/docs/adr"
fi

# Copy configuration template
echo "Copying configuration..."
if [[ ! -f "$TARGET_DIR/meta-process.yaml" ]]; then
    cp "$SCRIPT_DIR/templates/meta-process.yaml.example" "$TARGET_DIR/meta-process.yaml"
    echo -e "  ${GREEN}Created: meta-process.yaml${NC}"
else
    echo -e "  ${YELLOW}Skipped: meta-process.yaml (already exists)${NC}"
fi

# Copy scripts
echo "Copying scripts..."
CORE_SCRIPTS=(
    "check_claims.py"
    "check_plan_tests.py"
    "check_plan_blockers.py"
    "complete_plan.py"
    "parse_plan.py"
    "sync_plan_status.py"
    "safe_worktree_remove.py"
    "merge_pr.py"
    "finish_pr.py"
    "meta_status.py"
)

for script in "${CORE_SCRIPTS[@]}"; do
    if [[ -f "$SCRIPT_DIR/scripts/$script" ]]; then
        cp "$SCRIPT_DIR/scripts/$script" "$TARGET_DIR/scripts/meta/"
        echo -e "  ${GREEN}Copied: scripts/meta/$script${NC}"
    fi
done

if [[ "$MODE" == "--full" ]]; then
    FULL_SCRIPTS=(
        "check_doc_coupling.py"
        "sync_governance.py"
        "check_mock_usage.py"
        "check_adr_requirement.py"
        "validate_spec.py"
        "check_locked_files.py"
        "check_feature_coverage.py"
        "check_messages.py"
        "send_message.py"
    )
    for script in "${FULL_SCRIPTS[@]}"; do
        if [[ -f "$SCRIPT_DIR/scripts/$script" ]]; then
            cp "$SCRIPT_DIR/scripts/$script" "$TARGET_DIR/scripts/meta/"
            echo -e "  ${GREEN}Copied: scripts/meta/$script${NC}"
        fi
    done
fi

# Copy git hooks
echo "Copying git hooks..."
for hook in commit-msg pre-commit pre-push post-commit; do
    if [[ -f "$SCRIPT_DIR/hooks/git/$hook" ]]; then
        cp "$SCRIPT_DIR/hooks/git/$hook" "$TARGET_DIR/hooks/"
        chmod +x "$TARGET_DIR/hooks/$hook"
        echo -e "  ${GREEN}Copied: hooks/$hook${NC}"
    fi
done

# Copy Claude Code hooks
echo "Copying Claude Code hooks..."
CORE_CLAUDE_HOOKS=(
    "protect-main.sh"
    "check-cwd-valid.sh"
    "block-worktree-remove.sh"
)

for hook in "${CORE_CLAUDE_HOOKS[@]}"; do
    if [[ -f "$SCRIPT_DIR/hooks/claude/$hook" ]]; then
        cp "$SCRIPT_DIR/hooks/claude/$hook" "$TARGET_DIR/.claude/hooks/"
        chmod +x "$TARGET_DIR/.claude/hooks/$hook"
        echo -e "  ${GREEN}Copied: .claude/hooks/$hook${NC}"
    fi
done

if [[ "$MODE" == "--full" ]]; then
    FULL_CLAUDE_HOOKS=(
        "check-file-scope.sh"
        "check-references-reviewed.sh"
        "enforce-make-merge.sh"
        "check-inbox.sh"
        "notify-inbox-startup.sh"
    )
    for hook in "${FULL_CLAUDE_HOOKS[@]}"; do
        if [[ -f "$SCRIPT_DIR/hooks/claude/$hook" ]]; then
            cp "$SCRIPT_DIR/hooks/claude/$hook" "$TARGET_DIR/.claude/hooks/"
            chmod +x "$TARGET_DIR/.claude/hooks/$hook"
            echo -e "  ${GREEN}Copied: .claude/hooks/$hook${NC}"
        fi
    done
fi

# Copy templates
echo "Copying templates..."
if [[ ! -f "$TARGET_DIR/docs/plans/TEMPLATE.md" ]]; then
    cp "$SCRIPT_DIR/templates/plan.md.template" "$TARGET_DIR/docs/plans/TEMPLATE.md"
    echo -e "  ${GREEN}Created: docs/plans/TEMPLATE.md${NC}"
fi

if [[ ! -f "$TARGET_DIR/docs/plans/CLAUDE.md" ]]; then
    cp "$SCRIPT_DIR/templates/plans-index.md.template" "$TARGET_DIR/docs/plans/CLAUDE.md"
    echo -e "  ${GREEN}Created: docs/plans/CLAUDE.md${NC}"
fi

if [[ "$MODE" == "--full" ]]; then
    if [[ ! -f "$TARGET_DIR/scripts/doc_coupling.yaml" ]]; then
        cp "$SCRIPT_DIR/templates/doc_coupling.yaml.example" "$TARGET_DIR/scripts/doc_coupling.yaml"
        echo -e "  ${GREEN}Created: scripts/doc_coupling.yaml${NC}"
    fi

    if [[ ! -f "$TARGET_DIR/scripts/governance.yaml" ]]; then
        cp "$SCRIPT_DIR/templates/governance.yaml.example" "$TARGET_DIR/scripts/governance.yaml"
        echo -e "  ${GREEN}Created: scripts/governance.yaml${NC}"
    fi

    if [[ ! -f "$TARGET_DIR/acceptance_gates/EXAMPLE.yaml" ]]; then
        cp "$SCRIPT_DIR/templates/acceptance_gate.yaml.example" "$TARGET_DIR/acceptance_gates/EXAMPLE.yaml"
        echo -e "  ${GREEN}Created: acceptance_gates/EXAMPLE.yaml${NC}"
    fi
fi

# Copy Makefile additions
echo "Copying Makefile targets..."
if [[ -f "$SCRIPT_DIR/templates/Makefile.meta" ]]; then
    if [[ -f "$TARGET_DIR/Makefile" ]]; then
        if ! grep -q "# === META-PROCESS ===" "$TARGET_DIR/Makefile"; then
            echo "" >> "$TARGET_DIR/Makefile"
            cat "$SCRIPT_DIR/templates/Makefile.meta" >> "$TARGET_DIR/Makefile"
            echo -e "  ${GREEN}Appended meta-process targets to Makefile${NC}"
        else
            echo -e "  ${YELLOW}Skipped: Makefile (already has meta-process targets)${NC}"
        fi
    else
        cp "$SCRIPT_DIR/templates/Makefile.meta" "$TARGET_DIR/Makefile"
        echo -e "  ${GREEN}Created: Makefile${NC}"
    fi
fi

# Set up git hooks symlink
echo "Setting up git hooks..."
if [[ -d "$TARGET_DIR/.git" ]]; then
    cd "$TARGET_DIR"
    git config core.hooksPath hooks
    echo -e "  ${GREEN}Configured git to use hooks/ directory${NC}"
fi

# Copy pattern documentation
echo "Copying pattern documentation..."
mkdir -p "$TARGET_DIR/docs/meta-patterns"
cp -r "$SCRIPT_DIR/patterns/"*.md "$TARGET_DIR/docs/meta-patterns/" 2>/dev/null || true
echo -e "  ${GREEN}Copied pattern documentation to docs/meta-patterns/${NC}"

# Copy CLAUDE.md templates
echo "Copying CLAUDE.md templates..."

# Root CLAUDE.md (only if doesn't exist - don't overwrite custom configs)
if [[ ! -f "$TARGET_DIR/CLAUDE.md" ]]; then
    # Get project name from directory
    PROJECT_NAME=$(basename "$TARGET_DIR")
    REPO_PATH="$TARGET_DIR"

    # Create from template with substitutions
    sed -e "s|{{PROJECT_NAME}}|$PROJECT_NAME|g" \
        -e "s|{{REPO_PATH}}|$REPO_PATH|g" \
        -e "s|{{PRINCIPLE_1_NAME}}|Fail Loud|g" \
        -e "s|{{PRINCIPLE_1_DESC}}|No silent fallbacks|g" \
        -e "s|{{PRINCIPLE_2_NAME}}|Test First|g" \
        -e "s|{{PRINCIPLE_2_DESC}}|Write tests before implementation|g" \
        -e "s|{{PRINCIPLE_3_NAME}}|Explicit Over Implicit|g" \
        -e "s|{{PRINCIPLE_3_DESC}}|Clear configuration, no magic|g" \
        -e "s|{{TERM_1}}|term|g" \
        -e "s|{{TERM_1_ALT}}|alternate_term|g" \
        "$SCRIPT_DIR/templates/CLAUDE.md.root" > "$TARGET_DIR/CLAUDE.md"
    echo -e "  ${GREEN}Created: CLAUDE.md (customize for your project!)${NC}"
else
    echo -e "  ${YELLOW}Skipped: CLAUDE.md (already exists)${NC}"
fi

# Scripts CLAUDE.md
if [[ ! -f "$TARGET_DIR/scripts/CLAUDE.md" ]] && [[ -d "$TARGET_DIR/scripts" ]]; then
    cp "$SCRIPT_DIR/templates/CLAUDE.md.scripts" "$TARGET_DIR/scripts/CLAUDE.md"
    echo -e "  ${GREEN}Created: scripts/CLAUDE.md${NC}"
fi

# Tests CLAUDE.md
if [[ ! -f "$TARGET_DIR/tests/CLAUDE.md" ]] && [[ -d "$TARGET_DIR/tests" ]]; then
    cp "$SCRIPT_DIR/templates/CLAUDE.md.tests" "$TARGET_DIR/tests/CLAUDE.md"
    echo -e "  ${GREEN}Created: tests/CLAUDE.md${NC}"
fi

# docs/plans/CLAUDE.md (use the plans-index template if exists)
if [[ ! -f "$TARGET_DIR/docs/plans/CLAUDE.md" ]]; then
    if [[ -f "$SCRIPT_DIR/templates/CLAUDE.md.docs-plans" ]]; then
        cp "$SCRIPT_DIR/templates/CLAUDE.md.docs-plans" "$TARGET_DIR/docs/plans/CLAUDE.md"
        echo -e "  ${GREEN}Created: docs/plans/CLAUDE.md${NC}"
    fi
fi

# docs/adr/CLAUDE.md (only in full mode)
if [[ "$MODE" == "--full" ]] && [[ ! -f "$TARGET_DIR/docs/adr/CLAUDE.md" ]]; then
    cp "$SCRIPT_DIR/templates/CLAUDE.md.docs-adr" "$TARGET_DIR/docs/adr/CLAUDE.md"
    echo -e "  ${GREEN}Created: docs/adr/CLAUDE.md${NC}"
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Edit meta-process.yaml to configure patterns"
echo "  2. Add project-specific mappings to scripts/doc_coupling.yaml"
echo "  3. Run 'make status' to verify setup"
echo ""
echo "Quick start:"
echo "  make worktree           # Create isolated workspace"
echo "  # ... do work ..."
echo "  make pr-ready && make pr  # Ship it"
