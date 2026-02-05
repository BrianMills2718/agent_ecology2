#!/usr/bin/env python3
"""Extract relevant context for a file from GLOSSARY, ONTOLOGY, ADRs, PRDs, etc.

Given a source file, this script:
1. Parses the file to extract identifiers and terms
2. Matches against GLOSSARY entries
3. Matches against ONTOLOGY sections (formerly CONCEPTUAL_MODEL)
4. Extracts relevant ADR principles from governance mappings
5. Loads PRD capabilities and domain model concepts (Plan #294)

Usage:
    python scripts/extract_relevant_context.py src/world/ledger.py
    python scripts/extract_relevant_context.py src/world/ledger.py --format json
    python scripts/extract_relevant_context.py src/world/ledger.py --format hook
"""

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

import yaml


def get_repo_root() -> Path:
    """Get repository root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


REPO_ROOT = get_repo_root()


def extract_terms_from_python(file_path: Path) -> set[str]:
    """Extract identifiers and string literals from a Python file."""
    terms: set[str] = set()

    try:
        content = file_path.read_text()
    except Exception:
        return terms

    # Extract using AST
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            # Class names
            if isinstance(node, ast.ClassDef):
                terms.add(node.name)
                terms.add(node.name.lower())
            # Function names
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                terms.add(node.name)
                # Split snake_case
                for part in node.name.split("_"):
                    if len(part) > 2:
                        terms.add(part.lower())
            # Variable names and attributes
            elif isinstance(node, ast.Name):
                terms.add(node.id.lower())
            elif isinstance(node, ast.Attribute):
                terms.add(node.attr.lower())
            # String literals (for terms like "scrip", "principal")
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # Only short strings likely to be terms
                if 2 < len(node.value) < 30 and " " not in node.value:
                    terms.add(node.value.lower())
    except SyntaxError:
        pass

    # Also extract from comments and docstrings via regex
    # Look for capitalized terms that might be domain concepts
    for match in re.finditer(r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)*)\b', content):
        term = match.group(1)
        terms.add(term.lower())

    return terms


def load_glossary() -> dict[str, dict[str, str]]:
    """Load GLOSSARY.md and parse into structured entries."""
    glossary_path = REPO_ROOT / "docs" / "GLOSSARY.md"
    if not glossary_path.exists():
        return {}

    content = glossary_path.read_text()
    entries: dict[str, dict[str, str]] = {}

    # Parse Quick Reference table
    # Format: | Use | Not | Why |
    quick_ref_pattern = r'\|\s*`?([^`|]+)`?\s*\|\s*`?([^`|]+)`?\s*\|\s*([^|]+)\s*\|'
    in_quick_ref = False
    for line in content.split('\n'):
        if '## Quick Reference' in line:
            in_quick_ref = True
            continue
        if in_quick_ref and line.startswith('## '):
            in_quick_ref = False
        if in_quick_ref and '|' in line and '---' not in line and 'Use' not in line:
            match = re.match(quick_ref_pattern, line)
            if match:
                use_term = match.group(1).strip()
                not_term = match.group(2).strip()
                why = match.group(3).strip()
                entries[use_term.lower()] = {
                    "term": use_term,
                    "use_instead_of": not_term,
                    "why": why,
                    "type": "quick_reference"
                }

    # Parse term definitions from tables
    # Format: | **Term** | Definition | Properties |
    # or: | Term | Definition |
    current_section = ""
    for line in content.split('\n'):
        if line.startswith('## '):
            current_section = line.replace('## ', '').strip()
        elif line.startswith('| **') and '|' in line:
            # Bold term in table
            match = re.match(r'\|\s*\*\*([^*]+)\*\*\s*\|\s*([^|]+)', line)
            if match:
                term = match.group(1).strip()
                definition = match.group(2).strip()
                entries[term.lower()] = {
                    "term": term,
                    "definition": definition,
                    "section": current_section,
                    "type": "definition"
                }

    # Parse Deprecated Terms table
    in_deprecated = False
    for line in content.split('\n'):
        if '## Deprecated Terms' in line:
            in_deprecated = True
            continue
        if in_deprecated and line.startswith('## '):
            in_deprecated = False
        if in_deprecated and '|' in line and '---' not in line and "Don't Use" not in line:
            parts = [p.strip() for p in line.split('|')[1:-1]]
            if len(parts) >= 3:
                dont_use = parts[0].replace('**', '').strip()
                use_instead = parts[1].replace('**', '').strip()
                reason = parts[2].strip()
                entries[dont_use.lower()] = {
                    "term": dont_use,
                    "deprecated": True,
                    "use_instead": use_instead,
                    "reason": reason,
                    "type": "deprecated"
                }

    return entries


def load_ontology() -> dict[str, Any]:
    """Load ONTOLOGY.yaml (formerly CONCEPTUAL_MODEL.yaml)."""
    model_path = REPO_ROOT / "docs" / "ONTOLOGY.yaml"
    if not model_path.exists():
        return {}

    try:
        return yaml.safe_load(model_path.read_text())
    except Exception:
        return {}


def load_relationships() -> dict[str, Any]:
    """Load relationships.yaml for governance mappings."""
    rel_path = REPO_ROOT / "scripts" / "relationships.yaml"
    if not rel_path.exists():
        return {}

    try:
        return yaml.safe_load(rel_path.read_text())
    except Exception:
        return {}


def get_file_context(file_path: str, relationships: dict) -> dict[str, Any]:
    """Get PRD/domain model context for a file (Plan #294).

    Looks up file in file_context section, falls back to directory_defaults.
    Returns dict with prd, domain_model, and adr references.
    """
    result = {"prd": [], "domain_model": [], "adr": [], "source": None}

    # Normalize path - strip worktree prefix
    rel_path = file_path
    if rel_path.startswith(str(REPO_ROOT)):
        rel_path = str(Path(file_path).relative_to(REPO_ROOT))
    if "/worktrees/" in rel_path or rel_path.startswith("worktrees/"):
        rel_path = re.sub(r'^.*?worktrees/[^/]+/', '', rel_path)

    # Check explicit file_context first
    file_context = relationships.get("file_context", {})
    if rel_path in file_context:
        ctx = file_context[rel_path]
        result["prd"] = ctx.get("prd", [])
        result["domain_model"] = ctx.get("domain_model", [])
        result["adr"] = ctx.get("adr", [])
        result["source"] = "explicit"
        return result

    # Fall back to directory_defaults
    directory_defaults = relationships.get("directory_defaults", {})
    best_match = None
    best_match_len = 0

    for dir_pattern, defaults in directory_defaults.items():
        # Check if file path starts with directory pattern
        if rel_path.startswith(dir_pattern.rstrip('/')):
            if len(dir_pattern) > best_match_len:
                best_match = defaults
                best_match_len = len(dir_pattern)

    if best_match:
        result["prd"] = best_match.get("prd", [])
        result["domain_model"] = best_match.get("domain_model", [])
        result["adr"] = best_match.get("adr", [])
        result["source"] = "directory_default"

    return result


def load_prd_content(prd_refs: list[str]) -> list[dict]:
    """Load content from PRD files based on references.

    References format: 'agents#long-term-planning' or just 'agents'
    """
    results = []

    for ref in prd_refs:
        # Parse reference
        if "#" in ref:
            domain, section = ref.split("#", 1)
        else:
            domain = ref
            section = None

        prd_path = REPO_ROOT / "docs" / "prd" / f"{domain}.md"
        if not prd_path.exists():
            results.append({"domain": domain, "error": "PRD not found"})
            continue

        content = prd_path.read_text()

        if section:
            # Extract specific section
            section_content = extract_markdown_section(content, section)
            if section_content:
                results.append({
                    "domain": domain,
                    "section": section,
                    "content": section_content[:500]  # Limit size
                })
            else:
                results.append({
                    "domain": domain,
                    "section": section,
                    "error": f"Section '{section}' not found"
                })
        else:
            # Get overview only (first section after frontmatter)
            overview = extract_overview(content)
            results.append({
                "domain": domain,
                "content": overview[:300]
            })

    return results


def load_domain_model_content(dm_refs: list[str]) -> list[dict]:
    """Load content from domain model files based on references.

    References format: 'agents#Goal' or just 'agents'
    """
    results = []

    for ref in dm_refs:
        # Parse reference
        if "#" in ref:
            domain, concept = ref.split("#", 1)
        else:
            domain = ref
            concept = None

        dm_path = REPO_ROOT / "docs" / "domain_model" / f"{domain}.yaml"
        if not dm_path.exists():
            results.append({"domain": domain, "error": "Domain model not found"})
            continue

        try:
            dm = yaml.safe_load(dm_path.read_text())
        except Exception:
            results.append({"domain": domain, "error": "Failed to parse YAML"})
            continue

        if concept:
            # Extract specific concept
            concepts = dm.get("concepts", {})
            if concept in concepts:
                concept_data = concepts[concept]
                results.append({
                    "domain": domain,
                    "concept": concept,
                    "description": concept_data.get("description", "")[:200],
                    "enables": concept_data.get("enables", [])
                })
            else:
                results.append({
                    "domain": domain,
                    "concept": concept,
                    "error": f"Concept '{concept}' not found"
                })
        else:
            # Get all concept names
            concepts = dm.get("concepts", {})
            results.append({
                "domain": domain,
                "concepts": list(concepts.keys())
            })

    return results


def extract_markdown_section(content: str, section_id: str) -> str | None:
    """Extract a section from markdown by its header ID."""
    # Look for header with matching text (case-insensitive)
    pattern = rf'^###?\s+{re.escape(section_id)}\s*$'
    lines = content.split('\n')

    in_section = False
    section_lines = []

    for line in lines:
        if re.match(pattern, line, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            # Stop at next header of same or higher level
            if re.match(r'^###?\s+', line):
                break
            section_lines.append(line)

    return '\n'.join(section_lines).strip() if section_lines else None


def extract_overview(content: str) -> str:
    """Extract overview section from markdown (after frontmatter, before first ##)."""
    # Skip frontmatter
    if content.startswith('---'):
        end = content.find('---', 3)
        if end > 0:
            content = content[end + 3:]

    # Get content before first ## header
    lines = []
    for line in content.split('\n'):
        if line.startswith('## '):
            break
        lines.append(line)

    return '\n'.join(lines).strip()


def get_governance_for_file(file_path: str, relationships: dict) -> dict[str, Any]:
    """Get ADRs and context that govern a file."""
    result = {"adrs": [], "context": None, "coupled_docs": []}

    # Normalize path
    rel_path = file_path
    if rel_path.startswith(str(REPO_ROOT)):
        rel_path = str(Path(file_path).relative_to(REPO_ROOT))
    # Strip worktree prefix
    if "/worktrees/" in rel_path or rel_path.startswith("worktrees/"):
        rel_path = re.sub(r'^.*?worktrees/[^/]+/', '', rel_path)

    # Check governance entries
    for entry in relationships.get("governance", []):
        source = entry.get("source", "")
        if source == rel_path or rel_path.endswith(source):
            for adr_num in entry.get("adrs", []):
                adr_info = relationships.get("adrs", {}).get(adr_num, {})
                result["adrs"].append({
                    "number": adr_num,
                    "title": adr_info.get("title", f"ADR-{adr_num:04d}"),
                    "file": adr_info.get("file", "")
                })
            if entry.get("context"):
                result["context"] = entry["context"]

    # Check couplings
    for coupling in relationships.get("couplings", []):
        sources = coupling.get("sources", [])
        for source in sources:
            # Handle glob patterns simply
            if "*" in source:
                pattern = source.replace("**", ".*").replace("*", "[^/]*")
                if re.match(pattern, rel_path):
                    result["coupled_docs"].extend(coupling.get("docs", []))
            elif source == rel_path or rel_path.endswith(source):
                result["coupled_docs"].extend(coupling.get("docs", []))

    result["coupled_docs"] = list(set(result["coupled_docs"]))
    return result


def extract_glossary_matches(terms: set[str], glossary: dict) -> list[dict]:
    """Find glossary entries that match extracted terms."""
    matches = []
    seen = set()

    for term in terms:
        term_lower = term.lower()
        if term_lower in glossary and term_lower not in seen:
            seen.add(term_lower)
            matches.append(glossary[term_lower])

    # Sort: deprecated first (warnings), then definitions
    matches.sort(key=lambda x: (0 if x.get("deprecated") else 1, x.get("term", "")))
    return matches


def extract_conceptual_model_matches(terms: set[str], model: dict) -> dict[str, Any]:
    """Find conceptual model sections relevant to the terms."""
    matches = {}

    # Check if terms match top-level sections
    section_keywords = {
        "artifact": ["artifact", "artifacts", "executable", "policy", "content"],
        "actions": ["action", "actions", "read", "write", "invoke", "delete", "noop"],
        "kernel_interface": ["kernel", "kernel_state", "kernel_actions", "transfer"],
        "permission_system": ["permission", "contract", "access", "check_permission"],
        "resources": ["resource", "scrip", "depletable", "allocatable", "renewable", "balance"],
    }

    for section, keywords in section_keywords.items():
        if any(kw in terms for kw in keywords):
            if section in model:
                matches[section] = model[section]

    # Also check non_existence / forbidden terms
    if "relationships" in model:
        rel = model["relationships"]
        if "owner_term" in rel:
            matches["forbidden_terms"] = {"owner": rel["owner_term"]}

    return matches


def load_adr_principles(adr_file: str) -> list[str]:
    """Extract key principles from an ADR file."""
    adr_path = REPO_ROOT / "docs" / "adr" / adr_file
    if not adr_path.exists():
        return []

    content = adr_path.read_text()
    principles = []

    # Look for "Decision:" section
    in_decision = False
    for line in content.split('\n'):
        if line.startswith('## Decision'):
            in_decision = True
            continue
        if in_decision and line.startswith('## '):
            break
        if in_decision and line.strip().startswith('- '):
            principles.append(line.strip()[2:])
        elif in_decision and line.strip() and not line.startswith('#'):
            # Non-list decision text
            if len(line.strip()) < 200:  # Skip long paragraphs
                principles.append(line.strip())

    return principles[:5]  # Limit to top 5 principles


def run_semantic_search(terms: set[str], top_k: int = 5) -> list[dict]:
    """Run semantic search for additional relevant docs (Plan #289 Phase 2).

    Returns ADRs found via semantic search that supplement explicit mappings.
    """
    index_path = REPO_ROOT / "data" / "doc_index.json"
    if not index_path.exists():
        return []

    try:
        with open(index_path) as f:
            index = json.load(f)
    except Exception:
        return []

    # Simple BM25-like scoring (simplified for inline use)
    documents = index.get("documents", [])
    if not documents:
        return []

    # Build query from terms
    query_tokens = set()
    for term in terms:
        query_tokens.add(term.lower())
        # Also add parts of compound terms
        for part in term.split('_'):
            if len(part) > 2:
                query_tokens.add(part.lower())

    # Score documents
    scored = []
    for doc in documents:
        doc_tokens = set(doc.get("tokens", []))
        # Simple overlap score (Jaccard-like)
        overlap = len(query_tokens & doc_tokens)
        if overlap > 0:
            score = overlap / (len(query_tokens) + len(doc_tokens) - overlap + 1)
            scored.append((score, doc))

    # Sort by score
    scored.sort(key=lambda x: x[0], reverse=True)

    # Return top results (ADRs only for now, to supplement governance)
    results = []
    for score, doc in scored[:top_k * 2]:  # Get extra to filter
        if doc.get("type") == "adr":
            results.append({
                "number": doc.get("number"),
                "title": doc.get("title", ""),
                "file": doc.get("file", "").replace("docs/adr/", ""),
                "score": score,
                "principles": doc.get("principles", []),
            })
        if len(results) >= top_k:
            break

    return results


def extract_context_for_file(file_path: str) -> dict[str, Any]:
    """Main function: extract all relevant context for a file."""
    path = Path(file_path)
    if not path.is_absolute():
        path = REPO_ROOT / file_path

    # Handle worktree paths
    path_str = str(path)
    if "/worktrees/" in path_str:
        # Extract the actual file path within the worktree
        match = re.search(r'/worktrees/[^/]+/(.+)$', path_str)
        if match:
            actual_path = REPO_ROOT / match.group(1)
            if actual_path.exists():
                path = actual_path

    result = {
        "file": file_path,
        "glossary_matches": [],
        "conceptual_model": {},
        "governance": {},
        "adr_principles": [],
        "warnings": [],
        # Plan #294: PRD/domain model context
        "file_context": {},
        "prd_content": [],
        "domain_model_content": [],
    }

    # Extract terms from file
    if path.suffix == ".py" and path.exists():
        terms = extract_terms_from_python(path)
    else:
        terms = set()

    # Load reference docs
    glossary = load_glossary()
    model = load_ontology()
    relationships = load_relationships()

    # Plan #294: Get PRD/domain model context from file_context mappings
    file_ctx = get_file_context(file_path, relationships)
    result["file_context"] = file_ctx

    if file_ctx.get("prd"):
        result["prd_content"] = load_prd_content(file_ctx["prd"])
        # Warn if PRD not found
        for prd in result["prd_content"]:
            if prd.get("error"):
                result["warnings"].append(f"PRD: {prd['domain']} - {prd['error']}")

    if file_ctx.get("domain_model"):
        result["domain_model_content"] = load_domain_model_content(file_ctx["domain_model"])
        # Warn if domain model not found
        for dm in result["domain_model_content"]:
            if dm.get("error"):
                result["warnings"].append(f"Domain Model: {dm['domain']} - {dm['error']}")

    # Warn if no context links at all
    if not file_ctx.get("prd") and not file_ctx.get("domain_model") and file_ctx.get("source") is None:
        result["warnings"].append(
            f"No PRD/domain model context for this file. Consider adding to relationships.yaml file_context."
        )

    # Match against glossary
    result["glossary_matches"] = extract_glossary_matches(terms, glossary)

    # Check for deprecated terms (these become warnings)
    for match in result["glossary_matches"]:
        if match.get("deprecated"):
            result["warnings"].append(
                f"DEPRECATED TERM '{match['term']}': Use '{match.get('use_instead', '?')}' instead. {match.get('reason', '')}"
            )

    # Match against conceptual model
    result["conceptual_model"] = extract_conceptual_model_matches(terms, model)

    # Check forbidden terms
    if "forbidden_terms" in result["conceptual_model"]:
        for term, info in result["conceptual_model"]["forbidden_terms"].items():
            if term in terms:
                result["warnings"].append(f"FORBIDDEN TERM '{term}': {info}")

    # Get governance info
    result["governance"] = get_governance_for_file(file_path, relationships)

    # Extract ADR principles from explicit governance
    explicit_adr_nums = set()
    for adr in result["governance"].get("adrs", []):
        if adr.get("file"):
            explicit_adr_nums.add(adr.get("number"))
            principles = load_adr_principles(adr["file"])
            for p in principles:
                result["adr_principles"].append({
                    "adr": f"ADR-{adr['number']:04d}",
                    "title": adr.get("title", ""),
                    "principle": p,
                    "source": "governance",
                })

    # Semantic search for additional relevant ADRs (Plan #289)
    semantic_adrs = run_semantic_search(terms, top_k=3)
    result["semantic_matches"] = []
    for adr in semantic_adrs:
        adr_num = adr.get("number")
        if adr_num and adr_num not in explicit_adr_nums:
            result["semantic_matches"].append(adr)
            # Add top principle from semantic match
            if adr.get("principles"):
                result["adr_principles"].append({
                    "adr": f"ADR-{adr_num:04d}",
                    "title": adr.get("title", ""),
                    "principle": adr["principles"][0],
                    "source": "semantic",
                })

    return result


def format_for_hook(context: dict) -> str:
    """Format context for injection into a Claude Code hook."""
    lines = []

    # Warnings first (most important)
    if context.get("warnings"):
        lines.append("⚠️  WARNINGS:")
        for w in context["warnings"]:
            lines.append(f"   {w}")
        lines.append("")

    # ADR principles (explicit governance)
    explicit_principles = [p for p in context.get("adr_principles", []) if p.get("source") == "governance"]
    if explicit_principles:
        lines.append("📋 ADR PRINCIPLES (must follow):")
        for p in explicit_principles:
            lines.append(f"   [{p['adr']}] {p['principle']}")
        lines.append("")

    # ADR principles from semantic search (also relevant)
    semantic_principles = [p for p in context.get("adr_principles", []) if p.get("source") == "semantic"]
    if semantic_principles:
        lines.append("🔍 ALSO RELEVANT (semantic match):")
        for p in semantic_principles:
            lines.append(f"   [{p['adr']}] {p['principle']}")
        lines.append("")

    # Plan #294: PRD capabilities this file implements
    prd_content = context.get("prd_content", [])
    valid_prds = [p for p in prd_content if not p.get("error")]
    if valid_prds:
        lines.append("📋 PRD CAPABILITIES (this file implements):")
        for prd in valid_prds:
            if prd.get("section"):
                lines.append(f"   [{prd['domain']}#{prd['section']}]")
                # Show first 2 lines of content
                content_lines = prd.get("content", "").split('\n')[:2]
                for cl in content_lines:
                    if cl.strip():
                        lines.append(f"      {cl.strip()[:80]}")
            else:
                lines.append(f"   [{prd['domain']}] {prd.get('content', '')[:100]}")
        lines.append("")

    # Plan #294: Domain model concepts this file uses
    dm_content = context.get("domain_model_content", [])
    valid_dms = [d for d in dm_content if not d.get("error")]
    if valid_dms:
        lines.append("🧠 DOMAIN CONCEPTS (this file uses):")
        for dm in valid_dms:
            if dm.get("concept"):
                enables = dm.get("enables", [])
                enables_str = f" → enables: {', '.join(enables)}" if enables else ""
                lines.append(f"   • {dm['concept']}{enables_str}")
                if dm.get("description"):
                    # First line of description
                    desc = dm["description"].split('\n')[0].strip()[:80]
                    lines.append(f"      {desc}")
            else:
                concepts = dm.get("concepts", [])
                if concepts:
                    lines.append(f"   [{dm['domain']}] concepts: {', '.join(concepts[:5])}")
        lines.append("")

    # Governance context
    gov = context.get("governance", {})
    if gov.get("context"):
        lines.append("📌 GOVERNANCE CONTEXT:")
        for line in gov["context"].strip().split('\n'):
            lines.append(f"   {line}")
        lines.append("")

    # Key glossary terms (non-deprecated)
    glossary = [g for g in context.get("glossary_matches", []) if not g.get("deprecated")]
    if glossary:
        lines.append("📖 KEY TERMS:")
        for g in glossary[:10]:  # Limit to 10
            if g.get("type") == "quick_reference":
                lines.append(f"   • {g['term']}: Use instead of '{g.get('use_instead_of', '?')}' ({g.get('why', '')})")
            elif g.get("definition"):
                defn = g["definition"][:100] + "..." if len(g.get("definition", "")) > 100 else g.get("definition", "")
                lines.append(f"   • {g['term']}: {defn}")
        lines.append("")

    # Conceptual model highlights
    cm = context.get("conceptual_model", {})
    if "resources" in cm:
        lines.append("🏗️  RESOURCE MODEL:")
        res = cm["resources"]
        if "types" in res:
            for rtype, info in res["types"].items():
                examples = info.get("examples", [])
                lines.append(f"   • {rtype}: {', '.join(examples)}")
        lines.append("")

    # Coupled docs reminder
    if gov.get("coupled_docs"):
        lines.append("📄 DOCS TO CHECK AFTER EDITING:")
        for doc in gov["coupled_docs"][:5]:
            lines.append(f"   • {doc}")
        lines.append("")

    return "\n".join(lines)


def format_for_human(context: dict) -> str:
    """Format context for human-readable output."""
    lines = [f"Context for: {context['file']}", "=" * 60, ""]
    lines.append(format_for_hook(context))

    # Add raw data for debugging
    lines.append("-" * 60)
    lines.append("Raw extracted terms matched:")
    for g in context.get("glossary_matches", []):
        lines.append(f"  - {g.get('term')}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Extract relevant context for a file")
    parser.add_argument("file", help="File path to analyze")
    parser.add_argument("--format", choices=["human", "json", "hook"], default="human",
                        help="Output format")
    args = parser.parse_args()

    context = extract_context_for_file(args.file)

    if args.format == "json":
        print(json.dumps(context, indent=2))
    elif args.format == "hook":
        print(format_for_hook(context))
    else:
        print(format_for_human(context))


if __name__ == "__main__":
    main()
