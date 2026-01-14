#!/bin/bash
# Builds EXTERNAL_REVIEW_PACKAGE.md by concatenating documentation in reading order

set -e

DOCS_DIR="$(cd "$(dirname "$0")" && pwd)"
ROOT_DIR="$(dirname "$DOCS_DIR")"
OUTPUT="$DOCS_DIR/EXTERNAL_REVIEW_PACKAGE.md"
TARGET_DIR="$DOCS_DIR/architecture/target"

# Start with header
cat > "$OUTPUT" << 'HEADER'
# Agent Ecology - External Review Package

Generated: $(date '+%Y-%m-%d %H:%M')

This document concatenates all target architecture documentation
in recommended reading order for external review.

## Table of Contents

01. [Project Overview](#01-project-overview)
02. [Target Architecture Overview](#02-target-architecture-overview)
03. [Execution Model](#03-execution-model)
04. [Resource Model](#04-resource-model)
05. [Agent Model](#05-agent-model)
06. [Contract System](#06-contract-system)
07. [Minting System](#07-minting-system)
08. [Infrastructure](#08-infrastructure)
09. [Kernel](#09-kernel)
10. [Design Decisions and Rationale](#10-design-decisions-and-rationale)
11. [Implementation Gaps](#11-implementation-gaps)

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

# 01. Project Overview (from root README.md)
append_section "01" "Project Overview" "README.md"
append_content "$ROOT_DIR/README.md"

# 02. Target Architecture Overview
append_section "02" "Target Architecture Overview" "docs/architecture/target/01_README.md"
append_content "$TARGET_DIR/01_README.md"

# 03. Execution Model
append_section "03" "Execution Model" "docs/architecture/target/02_execution_model.md"
append_content "$TARGET_DIR/02_execution_model.md"

# 04. Resource Model
append_section "04" "Resource Model" "docs/architecture/target/04_resources.md"
append_content "$TARGET_DIR/04_resources.md"

# 05. Agent Model
append_section "05" "Agent Model" "docs/architecture/target/03_agents.md"
append_content "$TARGET_DIR/03_agents.md"

# 06. Contract System
append_section "06" "Contract System" "docs/architecture/target/05_contracts.md"
append_content "$TARGET_DIR/05_contracts.md"

# 07. Minting System
append_section "07" "Minting System" "docs/architecture/target/06_mint.md"
append_content "$TARGET_DIR/06_mint.md"

# 08. Infrastructure
append_section "08" "Infrastructure" "docs/architecture/target/07_infrastructure.md"
append_content "$TARGET_DIR/07_infrastructure.md"

# 09. Kernel
append_section "09" "Kernel" "docs/architecture/target/08_kernel.md"
append_content "$TARGET_DIR/08_kernel.md"

# 10. Design Decisions and Rationale
append_section "10" "Design Decisions and Rationale" "docs/DESIGN_CLARIFICATIONS.md"
append_content "$DOCS_DIR/DESIGN_CLARIFICATIONS.md"

# 11. Implementation Gaps
append_section "11" "Implementation Gaps" "docs/architecture/GAPS.md"
append_content "$DOCS_DIR/architecture/GAPS.md"

echo "Generated: $OUTPUT"
echo "Line count: $(wc -l < "$OUTPUT")"
