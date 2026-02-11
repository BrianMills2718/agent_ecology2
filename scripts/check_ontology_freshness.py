#!/usr/bin/env python3
"""Check ONTOLOGY.yaml freshness against actual source code via AST.

Compares documented fields/types against what the code actually defines.
Catches drift when code changes but docs/ONTOLOGY.yaml isn't updated.

Usage:
    python scripts/check_ontology_freshness.py           # Report drift
    python scripts/check_ontology_freshness.py --strict   # Exit 1 on drift

Checks:
  1. Artifact dataclass fields vs ONTOLOGY.yaml required_fields + optional_fields
  2. ActionType enum values vs ONTOLOGY.yaml actions categories
  3. conceptual_model.artifact.key_fields in relationships.yaml vs actual fields
  4. KernelState/KernelActions methods vs ONTOLOGY.yaml kernel_interface
"""

import ast
import sys
from pathlib import Path

import yaml


def extract_dataclass_fields(file_path: Path, class_name: str) -> list[str]:
    """Extract field names from a dataclass using AST.

    Extracts annotated assignments (the standard dataclass pattern)
    but NOT properties, methods, or class-level constants.
    """
    with open(file_path) as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            fields = []
            for item in node.body:
                if isinstance(item, ast.AnnAssign) and isinstance(
                    item.target, ast.Name
                ):
                    fields.append(item.target.id)
            return fields
    return []


def extract_enum_values(file_path: Path, class_name: str) -> list[str]:
    """Extract enum member values (the string values, not names) from an Enum class."""
    with open(file_path) as f:
        tree = ast.parse(f.read())

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            values = []
            for item in node.body:
                if isinstance(item, ast.Assign):
                    for target in item.targets:
                        if isinstance(target, ast.Name) and isinstance(
                            item.value, ast.Constant
                        ):
                            values.append(item.value.value)
            return values
    return []


def check_artifact_fields(ontology: dict) -> list[str]:
    """Check Artifact dataclass fields against ONTOLOGY.yaml."""
    errors = []

    artifact_section = ontology.get("artifact", {})
    required = set(artifact_section.get("required_fields", {}).keys())
    optional = set(artifact_section.get("optional_fields", {}).keys())
    ontology_fields = required | optional

    code_fields = set(
        extract_dataclass_fields(Path("src/world/artifacts.py"), "Artifact")
    )

    if not code_fields:
        errors.append("ERROR: Could not extract Artifact dataclass fields from source")
        return errors

    in_code_not_ontology = code_fields - ontology_fields
    in_ontology_not_code = ontology_fields - code_fields

    if in_code_not_ontology:
        for f in sorted(in_code_not_ontology):
            errors.append(
                f"DRIFT: Artifact field '{f}' exists in code but not in ONTOLOGY.yaml"
            )

    if in_ontology_not_code:
        for f in sorted(in_ontology_not_code):
            errors.append(
                f"STALE: Artifact field '{f}' in ONTOLOGY.yaml but not in code"
            )

    return errors


def check_action_types(ontology: dict) -> list[str]:
    """Check ActionType enum values against ONTOLOGY.yaml actions."""
    errors = []

    actions_section = ontology.get("actions", {})
    ontology_actions: set[str] = set()
    for category_name, category in actions_section.items():
        if isinstance(category, dict) and "operations" in category:
            ontology_actions.update(category["operations"])

    code_actions = set(
        extract_enum_values(Path("src/world/actions.py"), "ActionType")
    )

    if not code_actions:
        errors.append("ERROR: Could not extract ActionType enum from source")
        return errors

    in_code_not_ontology = code_actions - ontology_actions
    in_ontology_not_code = ontology_actions - code_actions

    if in_code_not_ontology:
        for a in sorted(in_code_not_ontology):
            errors.append(
                f"DRIFT: Action '{a}' exists in code but not in ONTOLOGY.yaml"
            )

    if in_ontology_not_code:
        for a in sorted(in_ontology_not_code):
            errors.append(
                f"STALE: Action '{a}' in ONTOLOGY.yaml but not in code"
            )

    return errors


def check_conceptual_model_key_fields() -> list[str]:
    """Check conceptual_model.artifact.key_fields in relationships.yaml."""
    errors = []

    rel_path = Path("scripts/relationships.yaml")
    if not rel_path.exists():
        return errors

    with open(rel_path) as f:
        data = yaml.safe_load(f) or {}

    cm = data.get("conceptual_model", {})
    artifact_cm = cm.get("artifact", {})
    key_fields = set(artifact_cm.get("key_fields", []))

    if not key_fields:
        return errors

    code_fields = set(
        extract_dataclass_fields(Path("src/world/artifacts.py"), "Artifact")
    )

    invalid = key_fields - code_fields
    if invalid:
        for f in sorted(invalid):
            errors.append(
                f"STALE: conceptual_model.artifact.key_fields has '{f}' "
                f"but field not in Artifact dataclass"
            )

    return errors


def check_kernel_interface_methods(ontology: dict) -> list[str]:
    """Check kernel_interface method signatures against ONTOLOGY.yaml."""
    errors = []

    ki_section = ontology.get("kernel_interface", {})

    for section_name in ("kernel_state", "kernel_actions"):
        section = ki_section.get(section_name, {})
        methods_list = section.get("methods", [])
        if not methods_list:
            continue

        # The ontology lists methods as strings like "get_balance(principal_id) -> int"
        # Extract method names (first word before the parenthesis)
        ontology_methods = set()
        for m in methods_list:
            if isinstance(m, str) and "(" in m:
                name = m.split("(")[0].strip()
                ontology_methods.add(name)

        # Map section to class name
        class_name = (
            "KernelState" if section_name == "kernel_state" else "KernelActions"
        )
        ki_path = Path("src/world/kernel_interface.py")

        with open(ki_path) as f:
            tree = ast.parse(f.read())

        code_methods: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith(
                        "_"
                    ):
                        code_methods.add(item.name)

        if not code_methods:
            continue

        in_code_not_ontology = code_methods - ontology_methods
        in_ontology_not_code = ontology_methods - code_methods

        if in_code_not_ontology:
            for m in sorted(in_code_not_ontology):
                errors.append(
                    f"DRIFT: {class_name}.{m}() exists in code "
                    f"but not in ONTOLOGY.yaml"
                )

        if in_ontology_not_code:
            for m in sorted(in_ontology_not_code):
                errors.append(
                    f"STALE: {class_name}.{m}() in ONTOLOGY.yaml but not in code"
                )

    return errors


def main() -> int:
    strict = "--strict" in sys.argv

    ontology_path = Path("docs/ONTOLOGY.yaml")
    if not ontology_path.exists():
        print("ERROR: docs/ONTOLOGY.yaml not found")
        return 1

    with open(ontology_path) as f:
        ontology = yaml.safe_load(f) or {}

    all_errors: list[str] = []

    # Check 1: Artifact fields
    print("Checking Artifact dataclass fields...")
    errors = check_artifact_fields(ontology)
    all_errors.extend(errors)
    if not errors:
        print("  OK")

    # Check 2: Action types
    print("Checking ActionType enum values...")
    errors = check_action_types(ontology)
    all_errors.extend(errors)
    if not errors:
        print("  OK")

    # Check 3: conceptual_model key_fields
    print("Checking conceptual_model.artifact.key_fields...")
    errors = check_conceptual_model_key_fields()
    all_errors.extend(errors)
    if not errors:
        print("  OK")

    # Check 4: kernel_interface methods
    print("Checking kernel_interface method signatures...")
    errors = check_kernel_interface_methods(ontology)
    all_errors.extend(errors)
    if not errors:
        print("  OK")

    if all_errors:
        print(
            f"\n{'ERRORS' if strict else 'WARNINGS'}: "
            f"{len(all_errors)} ontology drift issue(s)"
        )
        for e in all_errors:
            print(f"  {e}")
        if strict:
            print("\nFix docs/ONTOLOGY.yaml to match source code.")
            return 1
    else:
        print("\nPASSED: ontology matches source code")

    return 0


if __name__ == "__main__":
    sys.exit(main())
