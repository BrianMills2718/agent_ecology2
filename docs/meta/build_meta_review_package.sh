#!/bin/bash
# Builds META_REVIEW_PACKAGE.md by concatenating meta pattern documentation in reading order

set -e

META_DIR="$(cd "$(dirname "$0")" && pwd)"
OUTPUT="$META_DIR/META_REVIEW_PACKAGE.md"

# Start with header
cat > "$OUTPUT" << 'HEADER'
# Agent Ecology - Meta Patterns Review Package

Generated: $(date '+%Y-%m-%d %H:%M')

This document concatenates all meta pattern documentation
in recommended reading order for external review.

## Table of Contents

01. [Overview](#01-overview)
02. [CLAUDE.md Authoring](#02-claudemd-authoring)
03. [Testing Strategy](#03-testing-strategy)
04. [Mocking Policy](#04-mocking-policy)
05. [Mock Enforcement](#05-mock-enforcement)
06. [Git Hooks](#06-git-hooks)
07. [ADR](#07-adr)
08. [ADR Governance](#08-adr-governance)
09. [Documentation Graph](#09-documentation-graph)
10. [Doc-Code Coupling](#10-doc-code-coupling)
11. [Terminology](#11-terminology)
12. [Structured Logging](#12-structured-logging)
13. [Feature-Driven Development](#13-feature-driven-development)
14. [Feature Linkage](#14-feature-linkage)
15. [Plan Workflow](#15-plan-workflow)
16. [Plan Blocker Enforcement](#16-plan-blocker-enforcement)
17. [Verification Enforcement](#17-verification-enforcement)
18. [Claim System](#18-claim-system)
19. [Worktree Enforcement](#19-worktree-enforcement)
20. [Rebase Workflow](#20-rebase-workflow)
21. [PR Coordination](#21-pr-coordination)
22. [Human Review Pattern](#22-human-review-pattern)
23. [Plan Status Validation](#23-plan-status-validation)
24. [Phased ADR Pattern](#24-phased-adr-pattern)
25. [PR Review Process](#25-pr-review-process)
26. [Ownership Respect](#26-ownership-respect)

---

HEADER

# Fix the date (can't use command substitution in heredoc easily)
sed -i "s/\$(date '+%Y-%m-%d %H:%M')/$(date '+%Y-%m-%d %H:%M')/" "$OUTPUT"

# Function to append a section
append_section() {
    local num="$1"
    local title="$2"
    local source="$3"

    echo "" >> "$OUTPUT"
    echo "## $num. $title" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "*Source: \`$source\`*" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
}

# Function to append file content (skip the first heading line)
append_content() {
    local file="$1"
    # Skip first line if it's a markdown heading, then append rest
    tail -n +2 "$file" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "---" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
}

# 01. Overview
append_section "01" "Overview" "docs/meta/01_README.md"
append_content "$META_DIR/01_README.md"

# 02. CLAUDE.md Authoring
append_section "02" "CLAUDE.md Authoring" "docs/meta/02_claude-md-authoring.md"
append_content "$META_DIR/02_claude-md-authoring.md"

# 03. Testing Strategy
append_section "03" "Testing Strategy" "docs/meta/03_testing-strategy.md"
append_content "$META_DIR/03_testing-strategy.md"

# 04. Mocking Policy
append_section "04" "Mocking Policy" "docs/meta/04_mocking-policy.md"
append_content "$META_DIR/04_mocking-policy.md"

# 05. Mock Enforcement
append_section "05" "Mock Enforcement" "docs/meta/05_mock-enforcement.md"
append_content "$META_DIR/05_mock-enforcement.md"

# 06. Git Hooks
append_section "06" "Git Hooks" "docs/meta/06_git-hooks.md"
append_content "$META_DIR/06_git-hooks.md"

# 07. ADR
append_section "07" "ADR" "docs/meta/07_adr.md"
append_content "$META_DIR/07_adr.md"

# 08. ADR Governance
append_section "08" "ADR Governance" "docs/meta/08_adr-governance.md"
append_content "$META_DIR/08_adr-governance.md"

# 09. Documentation Graph
append_section "09" "Documentation Graph" "docs/meta/09_documentation-graph.md"
append_content "$META_DIR/09_documentation-graph.md"

# 10. Doc-Code Coupling
append_section "10" "Doc-Code Coupling" "docs/meta/10_doc-code-coupling.md"
append_content "$META_DIR/10_doc-code-coupling.md"

# 11. Terminology
append_section "11" "Terminology" "docs/meta/11_terminology.md"
append_content "$META_DIR/11_terminology.md"

# 12. Structured Logging
append_section "12" "Structured Logging" "docs/meta/12_structured-logging.md"
append_content "$META_DIR/12_structured-logging.md"

# 13. Feature-Driven Development
append_section "13" "Feature-Driven Development" "docs/meta/13_feature-driven-development.md"
append_content "$META_DIR/13_feature-driven-development.md"

# 14. Feature Linkage
append_section "14" "Feature Linkage" "docs/meta/14_feature-linkage.md"
append_content "$META_DIR/14_feature-linkage.md"

# 15. Plan Workflow
append_section "15" "Plan Workflow" "docs/meta/15_plan-workflow.md"
append_content "$META_DIR/15_plan-workflow.md"

# 16. Plan Blocker Enforcement
append_section "16" "Plan Blocker Enforcement" "docs/meta/16_plan-blocker-enforcement.md"
append_content "$META_DIR/16_plan-blocker-enforcement.md"

# 17. Verification Enforcement
append_section "17" "Verification Enforcement" "docs/meta/17_verification-enforcement.md"
append_content "$META_DIR/17_verification-enforcement.md"

# 18. Claim System
append_section "18" "Claim System" "docs/meta/18_claim-system.md"
append_content "$META_DIR/18_claim-system.md"

# 19. Worktree Enforcement
append_section "19" "Worktree Enforcement" "docs/meta/19_worktree-enforcement.md"
append_content "$META_DIR/19_worktree-enforcement.md"

# 20. Rebase Workflow
append_section "20" "Rebase Workflow" "docs/meta/20_rebase-workflow.md"
append_content "$META_DIR/20_rebase-workflow.md"

# 21. PR Coordination
append_section "21" "PR Coordination" "docs/meta/21_pr-coordination.md"
append_content "$META_DIR/21_pr-coordination.md"

# 22. Human Review Pattern
append_section "22" "Human Review Pattern" "docs/meta/22_human-review-pattern.md"
append_content "$META_DIR/22_human-review-pattern.md"

# 23. Plan Status Validation
append_section "23" "Plan Status Validation" "docs/meta/23_plan-status-validation.md"
append_content "$META_DIR/23_plan-status-validation.md"

# 24. Phased ADR Pattern
append_section "24" "Phased ADR Pattern" "docs/meta/24_phased-adr-pattern.md"
append_content "$META_DIR/24_phased-adr-pattern.md"

# 25. PR Review Process
append_section "25" "PR Review Process" "docs/meta/25_pr-review-process.md"
append_content "$META_DIR/25_pr-review-process.md"

# 26. Ownership Respect
append_section "26" "Ownership Respect" "docs/meta/26_ownership-respect.md"
append_content "$META_DIR/26_ownership-respect.md"

echo "Generated: $OUTPUT"
echo "Line count: $(wc -l < "$OUTPUT")"
