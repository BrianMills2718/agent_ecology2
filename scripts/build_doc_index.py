#!/usr/bin/env python3
"""Build searchable index of all documentation (Plan #289 Phase 2).

Parses and indexes:
- ADRs (title, decision, principles)
- GLOSSARY.md (terms and definitions)
- ONTOLOGY.yaml (entities and fields, formerly CONCEPTUAL_MODEL.yaml)
- Architecture docs (current/*.md)

Output: data/doc_index.json
"""

import argparse
import json
import re
import sys
from pathlib import Path

import yaml


def get_repo_root() -> Path:
    """Get repository root directory."""
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / ".git").exists():
            return parent
    return Path.cwd()


REPO_ROOT = get_repo_root()


def tokenize(text: str) -> list[str]:
    """Simple tokenization for BM25."""
    # Lowercase, split on non-alphanumeric, filter short tokens
    text = text.lower()
    tokens = re.split(r'[^a-z0-9_]+', text)
    return [t for t in tokens if len(t) > 2]


def parse_adr(adr_path: Path) -> dict | None:
    """Parse an ADR file into indexed format."""
    try:
        content = adr_path.read_text()
    except Exception:
        return None

    # Extract ADR number from filename
    match = re.match(r'(\d+)-', adr_path.name)
    if not match:
        return None
    adr_num = int(match.group(1))

    # Extract title (first # heading)
    title = ""
    for line in content.split('\n'):
        if line.startswith('# '):
            title = line[2:].strip()
            break

    # Extract decision section
    decision = ""
    in_decision = False
    decision_lines = []
    for line in content.split('\n'):
        if line.startswith('## Decision'):
            in_decision = True
            continue
        if in_decision and line.startswith('## '):
            break
        if in_decision:
            decision_lines.append(line)
    decision = '\n'.join(decision_lines).strip()

    # Extract key principles (bullet points in decision)
    principles = []
    for line in decision_lines:
        if line.strip().startswith('- '):
            principles.append(line.strip()[2:])
        elif line.strip().startswith('**') and line.strip().endswith('**'):
            # Bold statements are often key principles
            principles.append(line.strip().strip('*'))

    # Build searchable text
    searchable = f"{title} {decision}"

    return {
        "type": "adr",
        "id": f"ADR-{adr_num:04d}",
        "number": adr_num,
        "title": title,
        "file": str(adr_path.relative_to(REPO_ROOT)),
        "decision_summary": decision[:500] if len(decision) > 500 else decision,
        "principles": principles[:5],
        "tokens": tokenize(searchable),
    }


def parse_glossary(glossary_path: Path) -> list[dict]:
    """Parse GLOSSARY.md into indexed entries."""
    entries = []
    try:
        content = glossary_path.read_text()
    except Exception:
        return entries

    # Parse definition sections (## Term or ### Term)
    current_term = None
    current_def = []

    for line in content.split('\n'):
        # New term heading
        if line.startswith('## ') or line.startswith('### '):
            # Save previous term
            if current_term:
                definition = ' '.join(current_def).strip()
                entries.append({
                    "type": "glossary",
                    "id": f"GLOSSARY:{current_term}",
                    "term": current_term,
                    "definition": definition[:300] if len(definition) > 300 else definition,
                    "file": "docs/GLOSSARY.md",
                    "tokens": tokenize(f"{current_term} {definition}"),
                })

            # Start new term
            current_term = line.lstrip('#').strip()
            current_def = []
        elif current_term and line.strip():
            current_def.append(line.strip())

    # Don't forget last term
    if current_term:
        definition = ' '.join(current_def).strip()
        entries.append({
            "type": "glossary",
            "id": f"GLOSSARY:{current_term}",
            "term": current_term,
            "definition": definition[:300] if len(definition) > 300 else definition,
            "file": "docs/GLOSSARY.md",
            "tokens": tokenize(f"{current_term} {definition}"),
        })

    return entries


def parse_ontology(model_path: Path) -> list[dict]:
    """Parse ONTOLOGY.yaml into indexed entries (formerly parse_conceptual_model)."""
    entries = []
    try:
        content = model_path.read_text()
        model = yaml.safe_load(content)
    except Exception:
        return entries

    if not isinstance(model, dict):
        return entries

    # Index top-level sections
    for section_name, section_content in model.items():
        if section_name in ('version', 'last_updated'):
            continue

        # Build description from section content
        if isinstance(section_content, dict):
            desc_parts = []
            for key, value in section_content.items():
                if isinstance(value, str):
                    desc_parts.append(f"{key}: {value}")
                elif isinstance(value, list):
                    desc_parts.append(f"{key}: {', '.join(str(v) for v in value[:5])}")
            description = '; '.join(desc_parts)
        elif isinstance(section_content, str):
            description = section_content
        else:
            description = str(section_content)

        entries.append({
            "type": "ontology",
            "id": f"ONTOLOGY:{section_name}",
            "section": section_name,
            "description": description[:400] if len(description) > 400 else description,
            "file": "docs/ONTOLOGY.yaml",
            "tokens": tokenize(f"{section_name} {description}"),
        })

    return entries


def parse_architecture_doc(doc_path: Path) -> dict | None:
    """Parse an architecture doc into indexed format."""
    try:
        content = doc_path.read_text()
    except Exception:
        return None

    # Extract title
    title = doc_path.stem.replace('_', ' ').title()
    for line in content.split('\n'):
        if line.startswith('# '):
            title = line[2:].strip()
            break

    # Extract first paragraph as summary
    paragraphs = content.split('\n\n')
    summary = ""
    for p in paragraphs:
        p = p.strip()
        if p and not p.startswith('#') and not p.startswith('|') and not p.startswith('```'):
            summary = p[:300] if len(p) > 300 else p
            break

    # Extract headings for structure
    headings = []
    for line in content.split('\n'):
        if line.startswith('## '):
            headings.append(line[3:].strip())

    return {
        "type": "architecture",
        "id": f"ARCH:{doc_path.stem}",
        "title": title,
        "file": str(doc_path.relative_to(REPO_ROOT)),
        "summary": summary,
        "headings": headings[:10],
        "tokens": tokenize(f"{title} {summary} {' '.join(headings)}"),
    }


def build_index() -> dict:
    """Build the complete document index."""
    index = {
        "version": 1,
        "documents": [],
    }

    # Index ADRs
    adr_dir = REPO_ROOT / "docs" / "adr"
    if adr_dir.exists():
        for adr_file in sorted(adr_dir.glob("*.md")):
            if adr_file.name in ("CLAUDE.md", "README.md", "TEMPLATE.md"):
                continue
            doc = parse_adr(adr_file)
            if doc:
                index["documents"].append(doc)

    # Index GLOSSARY
    glossary_path = REPO_ROOT / "docs" / "GLOSSARY.md"
    if glossary_path.exists():
        index["documents"].extend(parse_glossary(glossary_path))

    # Index ONTOLOGY (formerly CONCEPTUAL_MODEL)
    model_path = REPO_ROOT / "docs" / "ONTOLOGY.yaml"
    if model_path.exists():
        index["documents"].extend(parse_ontology(model_path))

    # Index architecture docs
    arch_dir = REPO_ROOT / "docs" / "architecture" / "current"
    if arch_dir.exists():
        for doc_file in sorted(arch_dir.glob("*.md")):
            if doc_file.name in ("CLAUDE.md", "README.md"):
                continue
            doc = parse_architecture_doc(doc_file)
            if doc:
                index["documents"].append(doc)

    return index


def main() -> int:
    parser = argparse.ArgumentParser(description="Build document search index")
    parser.add_argument("--output", "-o", default="data/doc_index.json",
                        help="Output file path")
    parser.add_argument("--stats", action="store_true",
                        help="Print index statistics")
    args = parser.parse_args()

    index = build_index()

    # Ensure output directory exists
    output_path = REPO_ROOT / args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Write index
    with open(output_path, 'w') as f:
        json.dump(index, f, indent=2)

    print(f"Built index with {len(index['documents'])} documents")
    print(f"Output: {output_path}")

    if args.stats:
        print("\nDocument counts by type:")
        by_type: dict[str, int] = {}
        for doc in index["documents"]:
            doc_type = doc["type"]
            by_type[doc_type] = by_type.get(doc_type, 0) + 1
        for doc_type, count in sorted(by_type.items()):
            print(f"  {doc_type}: {count}")

        print("\nSample documents:")
        for doc in index["documents"][:3]:
            print(f"  - {doc['id']}: {doc.get('title', doc.get('term', doc.get('section', '?')))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
