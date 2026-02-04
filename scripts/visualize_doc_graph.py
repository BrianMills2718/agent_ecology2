#!/usr/bin/env python3
"""Visualize the documentation graph from relationships.yaml.

Usage:
    python scripts/visualize_doc_graph.py              # Generate PNG
    python scripts/visualize_doc_graph.py --format svg # Generate SVG
    python scripts/visualize_doc_graph.py --text       # ASCII text output

Requires graphviz: apt install graphviz OR brew install graphviz
"""

import argparse
import subprocess
import sys
from pathlib import Path

import yaml


def load_relationships() -> dict:
    """Load relationships.yaml."""
    path = Path("scripts/relationships.yaml")
    if not path.exists():
        print("Error: scripts/relationships.yaml not found", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        return yaml.safe_load(f) or {}


def generate_dot(data: dict) -> str:
    """Generate DOT graph from relationships data."""
    lines = [
        "digraph DocGraph {",
        '  rankdir=TB;',
        '  node [shape=box, fontname="Helvetica", fontsize=10];',
        '  edge [fontname="Helvetica", fontsize=8];',
        "",
        "  // Subgraph for ADRs",
        '  subgraph cluster_adrs {',
        '    label="ADRs (Decisions)";',
        '    style=filled;',
        '    color=lightblue;',
        '    node [style=filled, fillcolor=white];',
    ]

    # Add ADR nodes
    for adr_num, info in data.get("adrs", {}).items():
        title = info.get("title", "Unknown")[:30]
        lines.append(f'    adr_{adr_num} [label="ADR-{adr_num:04d}\\n{title}"];')

    lines.extend([
        "  }",
        "",
        "  // Subgraph for orientation docs",
        '  subgraph cluster_orientation {',
        '    label="Orientation (Read First)";',
        '    style=filled;',
        '    color=lightgreen;',
        '    node [style=filled, fillcolor=white];',
        '    doc_CLAUDE_MD [label="CLAUDE.md"];',
        '    doc_CORE_SYSTEMS [label="CORE_SYSTEMS.md"];',
        "  }",
        "",
        "  // Subgraph for reference docs",
        '  subgraph cluster_reference {',
        '    label="Reference";',
        '    style=filled;',
        '    color=lightyellow;',
        '    node [style=filled, fillcolor=white];',
        '    doc_CONCEPTUAL_MODEL [label="CONCEPTUAL_MODEL.yaml"];',
        '    doc_GLOSSARY [label="GLOSSARY.md"];',
        "  }",
        "",
        "  // Subgraph for current architecture docs",
        '  subgraph cluster_current {',
        '    label="Current Architecture";',
        '    style=filled;',
        '    color=lightpink;',
        '    node [style=filled, fillcolor=white];',
    ])

    # Add current/* docs
    current_docs = set()
    for coupling in data.get("couplings", []):
        for doc in coupling.get("docs", []):
            if "current/" in doc:
                doc_name = Path(doc).stem
                current_docs.add(doc_name)

    for doc in sorted(current_docs):
        safe_name = doc.replace("-", "_").replace(".", "_")
        lines.append(f'    doc_current_{safe_name} [label="{doc}.md"];')

    lines.extend([
        "  }",
        "",
        "  // Subgraph for source code",
        '  subgraph cluster_source {',
        '    label="Source Code";',
        '    style=filled;',
        '    color=lightgray;',
        '    node [style=filled, fillcolor=white, shape=ellipse];',
    ])

    # Add key source files from governance
    source_files = set()
    for entry in data.get("governance", []):
        src = entry.get("source", "")
        if src:
            source_files.add(src)

    for src in sorted(source_files):
        safe_name = src.replace("/", "_").replace(".", "_")
        short_name = Path(src).name
        lines.append(f'    src_{safe_name} [label="{short_name}"];')

    lines.extend([
        "  }",
        "",
        "  // Edges: ADR governs source",
    ])

    # Add governance edges
    for entry in data.get("governance", []):
        src = entry.get("source", "")
        if not src:
            continue
        safe_src = src.replace("/", "_").replace(".", "_")
        for adr_num in entry.get("adrs", []):
            lines.append(f'  adr_{adr_num} -> src_{safe_src} [label="governs", color=blue];')

    lines.append("")
    lines.append("  // Edges: source documented_by doc")

    # Add coupling edges (just a few key ones to avoid clutter)
    added_edges = set()
    for coupling in data.get("couplings", []):
        if coupling.get("soft"):
            continue  # Skip soft couplings for clarity
        for src in coupling.get("sources", [])[:2]:  # Limit sources
            if "**" in src or "*" in src:
                continue  # Skip globs
            safe_src = src.replace("/", "_").replace(".", "_")
            for doc in coupling.get("docs", []):
                if "current/" in doc:
                    doc_name = Path(doc).stem
                    safe_doc = doc_name.replace("-", "_").replace(".", "_")
                    edge_key = (safe_src, safe_doc)
                    if edge_key not in added_edges and f"src_{safe_src}" in "\n".join(lines):
                        lines.append(
                            f'  src_{safe_src} -> doc_current_{safe_doc} '
                            f'[label="documented_by", color=green];'
                        )
                        added_edges.add(edge_key)

    lines.append("")
    lines.append("  // Edges: target links to current")

    # Add target-current links
    for link in data.get("target_current_links", []):
        target = Path(link.get("target", "")).stem
        current = Path(link.get("current", "")).stem
        safe_current = current.replace("-", "_").replace(".", "_")
        lines.append(
            f'  target_{target} -> doc_current_{safe_current} '
            f'[label="implements", style=dashed, color=purple];'
        )

    lines.append("")
    lines.append("  // Hierarchy edges")
    lines.append('  doc_CLAUDE_MD -> doc_CORE_SYSTEMS [label="then read", style=dotted];')
    lines.append('  doc_CORE_SYSTEMS -> doc_CONCEPTUAL_MODEL [label="reference", style=dotted];')
    lines.append('  doc_CONCEPTUAL_MODEL -> doc_current_resources [label="details", style=dotted];')

    lines.append("}")
    return "\n".join(lines)


def generate_text(data: dict) -> str:
    """Generate text visualization."""
    lines = [
        "=" * 70,
        "DOCUMENTATION GRAPH",
        "=" * 70,
        "",
        "HIERARCHY (Read Order):",
        "  1. CLAUDE.md → Process workflow",
        "  2. CORE_SYSTEMS.md → System overview",
        "  3. CONCEPTUAL_MODEL.yaml → Exact entities",
        "  4. current/*.md → Implementation details",
        "  5. src/**/*.py → Source code",
        "",
        "-" * 70,
        "GOVERNANCE (ADR → Code):",
        "-" * 70,
    ]

    for entry in data.get("governance", []):
        src = entry.get("source", "")
        adrs = entry.get("adrs", [])
        adr_defs = data.get("adrs", {})
        adr_strs = []
        for a in adrs:
            title = adr_defs.get(a, {}).get("title", "?")
            adr_strs.append(f"ADR-{a:04d}")
        lines.append(f"  {', '.join(adr_strs)} → {src}")

    lines.extend([
        "",
        "-" * 70,
        "COUPLINGS (Code → Doc) - Strict only:",
        "-" * 70,
    ])

    for coupling in data.get("couplings", []):
        if coupling.get("soft"):
            continue
        sources = coupling.get("sources", [])
        docs = coupling.get("docs", [])
        src_str = ", ".join(Path(s).name for s in sources[:2])
        if len(sources) > 2:
            src_str += "..."
        doc_str = ", ".join(Path(d).name for d in docs)
        lines.append(f"  {src_str} → {doc_str}")

    lines.extend([
        "",
        "-" * 70,
        "TARGET ↔ CURRENT:",
        "-" * 70,
    ])

    for link in data.get("target_current_links", []):
        target = Path(link.get("target", "")).name
        current = Path(link.get("current", "")).name
        lines.append(f"  {target} ↔ {current}")

    lines.append("")
    lines.append("=" * 70)

    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Visualize documentation graph")
    parser.add_argument("--format", choices=["png", "svg", "dot"], default="png")
    parser.add_argument("--text", action="store_true", help="Text output instead of image")
    parser.add_argument("--output", "-o", help="Output file path")
    args = parser.parse_args()

    data = load_relationships()

    if args.text:
        print(generate_text(data))
        return 0

    dot_content = generate_dot(data)

    if args.format == "dot":
        output = args.output or "doc_graph.dot"
        with open(output, "w") as f:
            f.write(dot_content)
        print(f"Generated: {output}")
        return 0

    # Check if graphviz is installed
    try:
        subprocess.run(["dot", "-V"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: graphviz not installed. Install with:", file=sys.stderr)
        print("  apt install graphviz  # Debian/Ubuntu", file=sys.stderr)
        print("  brew install graphviz # macOS", file=sys.stderr)
        print("\nFalling back to text output:\n", file=sys.stderr)
        print(generate_text(data))
        return 1

    # Generate image
    output = args.output or f"doc_graph.{args.format}"
    result = subprocess.run(
        ["dot", f"-T{args.format}", "-o", output],
        input=dot_content.encode(),
        capture_output=True,
    )

    if result.returncode != 0:
        print(f"Error generating graph: {result.stderr.decode()}", file=sys.stderr)
        return 1

    print(f"Generated: {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
