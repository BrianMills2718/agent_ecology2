#!/usr/bin/env python3
"""Validate plan before implementation.

Queries the documentation graph (relationships.yaml) to surface:
- ADRs that govern affected files
- Target docs to check for consistency
- Current docs that need updating
- Low-certainty items in DESIGN_CLARIFICATIONS.md

Usage:
    python scripts/validate_plan.py --plan 28
    python scripts/validate_plan.py --plan 28 --json
    python scripts/validate_plan.py --list-adrs src/world/ledger.py
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


def load_relationships() -> dict[str, Any]:
    """Load the unified relationships config."""
    config_path = Path(__file__).parent / "relationships.yaml"
    if not config_path.exists():
        # Fall back to old configs if relationships.yaml doesn't exist yet
        print("Warning: relationships.yaml not found, using legacy configs", file=sys.stderr)
        return load_legacy_configs()

    with open(config_path) as f:
        return yaml.safe_load(f)


def load_legacy_configs() -> dict[str, Any]:
    """Load from governance.yaml and doc_coupling.yaml (fallback)."""
    scripts_dir = Path(__file__).parent

    result: dict[str, Any] = {"edges": [], "adrs": {}}

    # Load governance.yaml
    gov_path = scripts_dir / "governance.yaml"
    if gov_path.exists():
        with open(gov_path) as f:
            gov = yaml.safe_load(f)
            result["adrs"] = gov.get("adrs", {})
            for file_path, info in gov.get("files", {}).items():
                for adr_num in info.get("adrs", []):
                    result["edges"].append({
                        "from": f"adr/{adr_num:04d}",
                        "to": file_path,
                        "type": "governs",
                        "context": info.get("context", "")
                    })

    # Load doc_coupling.yaml
    coupling_path = scripts_dir / "doc_coupling.yaml"
    if coupling_path.exists():
        with open(coupling_path) as f:
            coupling = yaml.safe_load(f)
            for item in coupling.get("couplings", []):
                coupling_type = "soft" if item.get("soft") else "strict"
                for source in item.get("sources", []):
                    for doc in item.get("docs", []):
                        result["edges"].append({
                            "from": source,
                            "to": doc,
                            "type": "documented_by",
                            "coupling": coupling_type,
                            "description": item.get("description", "")
                        })

    return result


def load_plan(plan_num: int) -> dict[str, Any] | None:
    """Load a plan file and extract metadata."""
    plans_dir = Path("docs/plans")

    # Find plan file (could be NN_name.md or N_name.md)
    patterns = [f"{plan_num:02d}_*.md", f"{plan_num}_*.md"]
    for pattern in patterns:
        matches = list(plans_dir.glob(pattern))
        if matches:
            plan_path = matches[0]
            break
    else:
        return None

    content = plan_path.read_text()

    # Extract metadata
    result: dict[str, Any] = {
        "path": str(plan_path),
        "name": plan_path.stem,
        "files_to_change": [],
        "status": "Unknown"
    }

    # Extract status
    status_match = re.search(r'\*\*Status:\*\*\s*(.+)', content)
    if status_match:
        result["status"] = status_match.group(1).strip()

    # Extract files from "Files to Modify" or "Changes Required" table
    in_changes = False
    for line in content.split("\n"):
        if "## Changes" in line or "## Plan" in line or "Files to Modify" in line or "Changes Required" in line:
            in_changes = True
        elif line.startswith("## ") and in_changes and "Changes" not in line:
            in_changes = False
        elif in_changes and "|" in line and "`" in line:
            # Extract file path from table row like "| `src/module.py` | ... |"
            match = re.search(r'`([^`]+)`', line)
            if match:
                file_path = match.group(1)
                if file_path.startswith("src/") or file_path.startswith("tests/"):
                    result["files_to_change"].append(file_path)

    return result


def load_design_clarifications() -> list[dict[str, Any]]:
    """Load DESIGN_CLARIFICATIONS.md and extract certainty levels."""
    dc_path = Path("docs/DESIGN_CLARIFICATIONS.md")
    if not dc_path.exists():
        return []

    content = dc_path.read_text()
    items: list[dict[str, Any]] = []

    # Find items with certainty percentages
    # Pattern: ### N. Title ... **Certainty:** XX%
    current_item: dict[str, Any] | None = None

    for line in content.split("\n"):
        # New item header
        header_match = re.match(r'^###\s+(\d+)\.\s+(.+)', line)
        if header_match:
            if current_item:
                items.append(current_item)
            current_item = {
                "number": int(header_match.group(1)),
                "title": header_match.group(2).strip(),
                "certainty": None
            }

        # Certainty line
        if current_item:
            cert_match = re.search(r'\*\*Certainty:\*\*\s*(\d+)%', line)
            if cert_match:
                current_item["certainty"] = int(cert_match.group(1))

    if current_item:
        items.append(current_item)

    return items


def find_governing_adrs(file_path: str, config: dict[str, Any]) -> list[dict[str, Any]]:
    """Find ADRs that govern a specific file."""
    adrs = []

    for edge in config.get("edges", []):
        if edge.get("type") != "governs":
            continue

        targets = edge.get("to", [])
        if isinstance(targets, str):
            targets = [targets]

        for target in targets:
            # Handle namespace prefixes
            if target.startswith("source/"):
                target = target.replace("source/", "")

            if target == file_path or file_path.endswith(target):
                # Extract ADR info
                adr_ref = edge.get("from", "")
                adr_match = re.search(r'adr/(\d+)', adr_ref)
                if adr_match:
                    adr_num = int(adr_match.group(1))
                    adr_info = config.get("adrs", {}).get(adr_num, {})
                    adrs.append({
                        "number": adr_num,
                        "title": adr_info.get("title", f"ADR-{adr_num:04d}"),
                        "file": adr_info.get("file", f"{adr_num:04d}-unknown.md"),
                        "context": edge.get("context", "")
                    })

    return adrs


def find_coupled_docs(file_path: str, config: dict[str, Any], coupling_type: str = "strict") -> list[dict[str, Any]]:
    """Find docs coupled to a specific file."""
    docs = []

    for edge in config.get("edges", []):
        if edge.get("type") != "documented_by":
            continue
        if edge.get("coupling") != coupling_type:
            continue

        sources = edge.get("from", [])
        if isinstance(sources, str):
            sources = [sources]

        for source in sources:
            # Handle namespace prefixes and globs
            source_clean = source.replace("source/", "").replace("scripts/", "").replace("ci/", "")

            # Check for match (exact or glob)
            if source_clean == file_path or file_path.endswith(source_clean):
                target = edge.get("to", "")
                if isinstance(target, str):
                    docs.append({
                        "path": target,
                        "description": edge.get("description", "")
                    })

    return docs


def validate_plan(plan_num: int, config: dict[str, Any]) -> dict[str, Any]:
    """Validate a plan and return findings."""
    plan = load_plan(plan_num)
    if not plan:
        return {"error": f"Plan {plan_num} not found"}

    result: dict[str, Any] = {
        "plan": plan_num,
        "name": plan["name"],
        "status": plan["status"],
        "files_to_change": plan["files_to_change"],
        "governing_adrs": [],
        "docs_to_update": [],
        "uncertainties": [],
        "warnings": []
    }

    # Find governing ADRs for all files
    seen_adrs: set[int] = set()
    for file_path in plan["files_to_change"]:
        for adr in find_governing_adrs(file_path, config):
            if adr["number"] not in seen_adrs:
                seen_adrs.add(adr["number"])
                result["governing_adrs"].append(adr)

    # Find coupled docs for all files
    seen_docs: set[str] = set()
    for file_path in plan["files_to_change"]:
        for doc in find_coupled_docs(file_path, config, "strict"):
            if doc["path"] not in seen_docs:
                seen_docs.add(doc["path"])
                result["docs_to_update"].append(doc)

    # Check for low-certainty items in DESIGN_CLARIFICATIONS
    dc_items = load_design_clarifications()
    for item in dc_items:
        if item["certainty"] is not None and item["certainty"] < 70:
            result["uncertainties"].append(item)

    # Add warnings
    if not plan["files_to_change"]:
        result["warnings"].append("No files listed in Changes Required section")

    if plan["status"] == "✅ Complete":
        result["warnings"].append("Plan is already marked complete")

    return result


def print_validation_result(result: dict[str, Any]) -> None:
    """Print validation result in human-readable format."""
    if "error" in result:
        print(f"Error: {result['error']}")
        return

    print(f"Checking Plan #{result['plan']}: {result['name']}")
    print(f"Status: {result['status']}")
    print()

    if result["files_to_change"]:
        print("Files to change:")
        for f in result["files_to_change"]:
            print(f"  - {f}")
        print()

    if result["governing_adrs"]:
        print("ADRs that govern affected files:")
        for adr in result["governing_adrs"]:
            print(f"  - ADR-{adr['number']:04d}: {adr['title']}")
            if adr.get("context"):
                for line in adr["context"].strip().split("\n"):
                    print(f"      {line}")
        print()

    if result["docs_to_update"]:
        print("Current docs that need updating:")
        for doc in result["docs_to_update"]:
            print(f"  - {doc['path']}")
            if doc.get("description"):
                print(f"      ({doc['description']})")
        print()

    if result["uncertainties"]:
        print("DESIGN_CLARIFICATIONS items with <70% certainty:")
        for item in result["uncertainties"]:
            print(f"  - #{item['number']} {item['title']} ({item['certainty']}%)")
        print()

    if result["warnings"]:
        print("Warnings:")
        for w in result["warnings"]:
            print(f"  ⚠️  {w}")
        print()

    # Summary
    issues = len(result["uncertainties"]) + len(result["warnings"])
    if issues > 0:
        print(f"⚠️  {issues} issue(s) found - review before implementing")
    else:
        print("✅ No issues found - ready to implement")


def list_adrs_for_file(file_path: str, config: dict[str, Any]) -> None:
    """List ADRs governing a specific file."""
    adrs = find_governing_adrs(file_path, config)

    if not adrs:
        print(f"No ADRs govern {file_path}")
        return

    print(f"ADRs governing {file_path}:")
    for adr in adrs:
        print(f"  - ADR-{adr['number']:04d}: {adr['title']}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate plan before implementation")
    parser.add_argument("--plan", type=int, help="Plan number to validate")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--list-adrs", type=str, metavar="FILE", help="List ADRs governing a file")

    args = parser.parse_args()

    config = load_relationships()

    if args.list_adrs:
        list_adrs_for_file(args.list_adrs, config)
        return 0

    if args.plan:
        result = validate_plan(args.plan, config)

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print_validation_result(result)

        # Exit with error if issues found
        if "error" in result:
            return 1
        if result.get("uncertainties") or result.get("warnings"):
            return 1
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
