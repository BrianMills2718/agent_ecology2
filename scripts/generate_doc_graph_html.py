#!/usr/bin/env python3
"""Generate interactive HTML visualization of the documentation graph.

Usage:
    python scripts/generate_doc_graph_html.py                    # Generate doc_graph.html
    python scripts/generate_doc_graph_html.py -o custom.html     # Custom output path
    python scripts/generate_doc_graph_html.py --serve            # Generate and open in browser

The generated HTML is self-contained (includes D3.js from CDN) and can be
opened directly in any browser.
"""

import argparse
import json
import subprocess
import sys
import webbrowser
from pathlib import Path

import yaml

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Documentation Graph - Agent Ecology</title>
    <script src="https://d3js.org/d3.v7.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #1a1a2e;
            color: #eee;
            overflow: hidden;
        }
        #container {
            display: flex;
            height: 100vh;
        }
        #sidebar {
            width: 320px;
            background: #16213e;
            padding: 20px;
            overflow-y: auto;
            border-right: 1px solid #0f3460;
        }
        #graph {
            flex: 1;
            position: relative;
        }
        h1 {
            font-size: 1.4rem;
            margin-bottom: 20px;
            color: #e94560;
        }
        h2 {
            font-size: 1rem;
            margin: 20px 0 10px;
            color: #0f3460;
            background: #e94560;
            padding: 5px 10px;
            border-radius: 4px;
        }
        .legend {
            margin-bottom: 20px;
        }
        .legend-item {
            display: flex;
            align-items: center;
            margin: 8px 0;
            font-size: 0.85rem;
        }
        .legend-color {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            margin-right: 10px;
        }
        #details {
            background: #0f3460;
            border-radius: 8px;
            padding: 15px;
            margin-top: 20px;
        }
        #details h3 {
            color: #e94560;
            margin-bottom: 10px;
        }
        #details p {
            font-size: 0.85rem;
            line-height: 1.5;
            color: #aaa;
        }
        #details .label {
            color: #4ecca3;
            font-weight: bold;
        }
        .controls {
            margin-top: 20px;
            padding-top: 20px;
            border-top: 1px solid #0f3460;
        }
        .controls label {
            display: block;
            margin: 10px 0 5px;
            font-size: 0.85rem;
            color: #aaa;
        }
        .controls input[type="range"] {
            width: 100%;
        }
        .controls button {
            margin-top: 10px;
            padding: 8px 16px;
            background: #e94560;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 0.85rem;
        }
        .controls button:hover {
            background: #ff6b6b;
        }
        svg {
            width: 100%;
            height: 100%;
        }
        .node {
            cursor: pointer;
        }
        .node text {
            font-size: 11px;
            fill: #fff;
            pointer-events: none;
        }
        .link {
            stroke-opacity: 0.6;
        }
        .link-label {
            font-size: 9px;
            fill: #888;
        }
        #tooltip {
            position: absolute;
            background: #16213e;
            border: 1px solid #0f3460;
            border-radius: 6px;
            padding: 10px 14px;
            font-size: 0.85rem;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            max-width: 300px;
            z-index: 1000;
        }
        #tooltip.visible {
            opacity: 1;
        }
        #tooltip .title {
            font-weight: bold;
            color: #e94560;
            margin-bottom: 5px;
        }
        #tooltip .type {
            color: #4ecca3;
            font-size: 0.75rem;
            margin-bottom: 5px;
        }
        #search {
            width: 100%;
            padding: 8px 12px;
            background: #0f3460;
            border: 1px solid #1a1a2e;
            border-radius: 4px;
            color: #eee;
            font-size: 0.9rem;
            margin-bottom: 15px;
        }
        #search::placeholder {
            color: #666;
        }
    </style>
</head>
<body>
    <div id="container">
        <div id="sidebar">
            <h1>📚 Doc Graph</h1>
            <input type="text" id="search" placeholder="Search nodes...">

            <div class="legend">
                <div class="legend-item">
                    <div class="legend-color" style="background: #e94560;"></div>
                    <span>ADRs (Decisions)</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #4ecca3;"></div>
                    <span>Orientation Docs</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #ffd93d;"></div>
                    <span>Reference Docs</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #6c5ce7;"></div>
                    <span>Current Architecture</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #74b9ff;"></div>
                    <span>Target Architecture</span>
                </div>
                <div class="legend-item">
                    <div class="legend-color" style="background: #a8a8a8;"></div>
                    <span>Source Code</span>
                </div>
                <hr style="border-color: #0f3460; margin: 15px 0;">
                <div class="legend-item">
                    <div style="width: 30px; height: 2px; background: #4ecca3; margin-right: 10px;"></div>
                    <span>Strict coupling</span>
                </div>
                <div class="legend-item">
                    <div style="width: 30px; height: 2px; background: #2d8a6e; margin-right: 10px; border-style: dashed;"></div>
                    <span>Soft coupling</span>
                </div>
            </div>

            <div id="details">
                <h3>Select a node</h3>
                <p>Click on any node to see details</p>
            </div>

            <div class="controls">
                <label>Link Distance</label>
                <input type="range" id="linkDistance" min="50" max="300" value="150">
                <label>Charge Strength</label>
                <input type="range" id="chargeStrength" min="-500" max="-50" value="-200">
                <button onclick="resetZoom()">Reset View</button>
            </div>
        </div>
        <div id="graph">
            <div id="tooltip"></div>
        </div>
    </div>

    <script>
        const graphData = GRAPH_DATA_PLACEHOLDER;

        // Color scheme
        const colors = {
            adr: '#e94560',
            orientation: '#4ecca3',
            reference: '#ffd93d',
            current: '#6c5ce7',
            target: '#74b9ff',
            source: '#a8a8a8'
        };

        const linkColors = {
            governs: '#e94560',
            documented_by: '#4ecca3',
            documented_by_soft: '#2d8a6e',
            implements: '#74b9ff',
            hierarchy: '#ffd93d'
        };

        // Set up SVG
        const container = document.getElementById('graph');
        const width = container.clientWidth;
        const height = container.clientHeight;

        const svg = d3.select('#graph')
            .append('svg')
            .attr('width', width)
            .attr('height', height);

        // Add zoom behavior
        const g = svg.append('g');
        const zoom = d3.zoom()
            .scaleExtent([0.1, 4])
            .on('zoom', (event) => g.attr('transform', event.transform));
        svg.call(zoom);

        // Create simulation
        const simulation = d3.forceSimulation(graphData.nodes)
            .force('link', d3.forceLink(graphData.links).id(d => d.id).distance(150))
            .force('charge', d3.forceManyBody().strength(-200))
            .force('center', d3.forceCenter(width / 2, height / 2))
            .force('collision', d3.forceCollide().radius(40));

        // Draw links
        const link = g.append('g')
            .selectAll('line')
            .data(graphData.links)
            .join('line')
            .attr('class', 'link')
            .attr('stroke', d => linkColors[d.type] || '#666')
            .attr('stroke-width', d => d.type === 'governs' ? 2 : 1.5)
            .attr('stroke-dasharray', d =>
                d.type === 'implements' ? '5,5' :
                d.type === 'documented_by_soft' ? '3,3' : null);

        // Draw link labels
        const linkLabel = g.append('g')
            .selectAll('text')
            .data(graphData.links)
            .join('text')
            .attr('class', 'link-label')
            .text(d => d.type);

        // Draw nodes
        const node = g.append('g')
            .selectAll('g')
            .data(graphData.nodes)
            .join('g')
            .attr('class', 'node')
            .call(d3.drag()
                .on('start', dragstarted)
                .on('drag', dragged)
                .on('end', dragended));

        // Node circles
        node.append('circle')
            .attr('r', d => d.type === 'source' ? 8 : 12)
            .attr('fill', d => colors[d.type] || '#666')
            .attr('stroke', '#fff')
            .attr('stroke-width', 1.5);

        // Node labels
        node.append('text')
            .attr('dx', 15)
            .attr('dy', 4)
            .text(d => d.label);

        // Tooltip
        const tooltip = d3.select('#tooltip');

        node.on('mouseover', (event, d) => {
            tooltip
                .html(`<div class="title">${d.label}</div>
                       <div class="type">${d.type}</div>
                       ${d.description ? `<div>${d.description}</div>` : ''}`)
                .classed('visible', true)
                .style('left', (event.pageX + 10) + 'px')
                .style('top', (event.pageY - 10) + 'px');
        })
        .on('mouseout', () => tooltip.classed('visible', false))
        .on('click', (event, d) => showDetails(d));

        // Update positions on tick
        simulation.on('tick', () => {
            link
                .attr('x1', d => d.source.x)
                .attr('y1', d => d.source.y)
                .attr('x2', d => d.target.x)
                .attr('y2', d => d.target.y);

            linkLabel
                .attr('x', d => (d.source.x + d.target.x) / 2)
                .attr('y', d => (d.source.y + d.target.y) / 2);

            node.attr('transform', d => `translate(${d.x},${d.y})`);
        });

        // Drag functions
        function dragstarted(event) {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            event.subject.fx = event.subject.x;
            event.subject.fy = event.subject.y;
        }

        function dragged(event) {
            event.subject.fx = event.x;
            event.subject.fy = event.y;
        }

        function dragended(event) {
            if (!event.active) simulation.alphaTarget(0);
            event.subject.fx = null;
            event.subject.fy = null;
        }

        // Show details in sidebar
        function showDetails(d) {
            const details = document.getElementById('details');
            let html = `<h3>${d.label}</h3>`;
            html += `<p><span class="label">Type:</span> ${d.type}</p>`;
            if (d.path) html += `<p><span class="label">Path:</span> ${d.path}</p>`;
            if (d.description) html += `<p><span class="label">Description:</span> ${d.description}</p>`;

            // Find connected nodes
            const connected = graphData.links
                .filter(l => l.source.id === d.id || l.target.id === d.id)
                .map(l => {
                    const other = l.source.id === d.id ? l.target : l.source;
                    return `${l.type} → ${other.label}`;
                });

            if (connected.length > 0) {
                html += `<p><span class="label">Connections:</span></p>`;
                html += `<ul style="margin-left: 20px; font-size: 0.8rem;">`;
                connected.forEach(c => html += `<li>${c}</li>`);
                html += `</ul>`;
            }

            details.innerHTML = html;
        }

        // Reset zoom
        function resetZoom() {
            svg.transition().duration(750).call(
                zoom.transform,
                d3.zoomIdentity.translate(width / 2, height / 2).scale(0.8)
            );
        }

        // Search
        document.getElementById('search').addEventListener('input', (e) => {
            const term = e.target.value.toLowerCase();
            node.style('opacity', d =>
                term === '' || d.label.toLowerCase().includes(term) ? 1 : 0.2
            );
            link.style('opacity', d => {
                if (term === '') return 0.6;
                return d.source.label.toLowerCase().includes(term) ||
                       d.target.label.toLowerCase().includes(term) ? 0.6 : 0.1;
            });
        });

        // Controls
        document.getElementById('linkDistance').addEventListener('input', (e) => {
            simulation.force('link').distance(+e.target.value);
            simulation.alpha(0.3).restart();
        });

        document.getElementById('chargeStrength').addEventListener('input', (e) => {
            simulation.force('charge').strength(+e.target.value);
            simulation.alpha(0.3).restart();
        });

        // Initial zoom to fit
        setTimeout(resetZoom, 500);
    </script>
</body>
</html>
'''


def load_relationships() -> dict:
    """Load relationships.yaml."""
    path = Path("scripts/relationships.yaml")
    if not path.exists():
        print("Error: scripts/relationships.yaml not found", file=sys.stderr)
        sys.exit(1)

    with open(path) as f:
        return yaml.safe_load(f) or {}


def build_graph_data(data: dict) -> dict:
    """Build D3-compatible graph data from relationships."""
    nodes = []
    links = []
    node_ids = set()

    def add_node(id: str, label: str, type: str, **extra):
        if id not in node_ids:
            node_ids.add(id)
            nodes.append({"id": id, "label": label, "type": type, **extra})

    # Add ADRs
    for adr_num, info in data.get("adrs", {}).items():
        add_node(
            f"adr_{adr_num}",
            f"ADR-{adr_num:04d}",
            "adr",
            description=info.get("title", ""),
            path=f"docs/adr/{info.get('file', '')}",
        )

    # Add orientation docs
    add_node("doc_CLAUDE", "CLAUDE.md", "orientation", path="CLAUDE.md")
    add_node(
        "doc_CORE_SYSTEMS",
        "CORE_SYSTEMS.md",
        "orientation",
        path="docs/architecture/current/CORE_SYSTEMS.md",
    )

    # Add reference docs
    add_node(
        "doc_ONTOLOGY",
        "ONTOLOGY.yaml",
        "reference",
        path="docs/ONTOLOGY.yaml",
    )
    add_node("doc_GLOSSARY", "GLOSSARY.md", "reference", path="docs/GLOSSARY.md")

    # Add current docs from couplings
    current_docs = set()
    for coupling in data.get("couplings", []):
        for doc in coupling.get("docs", []):
            if "current/" in doc:
                current_docs.add(doc)

    for doc in current_docs:
        doc_name = Path(doc).stem
        add_node(
            f"doc_current_{doc_name}",
            f"{doc_name}.md",
            "current",
            path=doc,
            description=next(
                (
                    c.get("description", "")
                    for c in data.get("couplings", [])
                    if doc in c.get("docs", [])
                ),
                "",
            ),
        )

    # Add target docs from target_current_links
    for link in data.get("target_current_links", []):
        target = link.get("target", "")
        target_name = Path(target).stem
        add_node(
            f"doc_target_{target_name}",
            f"{target_name}.md",
            "target",
            path=target,
            description=link.get("description", ""),
        )

    # Add ALL source files from couplings (not just governed ones)
    all_sources = set()
    for coupling in data.get("couplings", []):
        for src in coupling.get("sources", []):
            # Skip glob patterns
            if "*" not in src and src.endswith(".py"):
                all_sources.add(src)

    # Also add governed sources
    for entry in data.get("governance", []):
        src = entry.get("source", "")
        if src:
            all_sources.add(src)

    # Create source nodes
    for src in all_sources:
        src_name = Path(src).name
        # Get governance context if any
        gov_context = ""
        for entry in data.get("governance", []):
            if entry.get("source") == src:
                gov_context = entry.get("context", "").strip()[:100]
                break
        add_node(
            f"src_{src.replace('/', '_').replace('.', '_')}",
            src_name,
            "source",
            path=src,
            description=gov_context,
        )

    # Add governance links (ADR -> source)
    for entry in data.get("governance", []):
        src = entry.get("source", "")
        if not src:
            continue
        src_id = f"src_{src.replace('/', '_').replace('.', '_')}"
        for adr_num in entry.get("adrs", []):
            links.append({"source": f"adr_{adr_num}", "target": src_id, "type": "governs"})

    # Add ALL coupling links (source -> doc)
    for coupling in data.get("couplings", []):
        is_soft = coupling.get("soft", False)
        link_type = "documented_by_soft" if is_soft else "documented_by"

        for src in coupling.get("sources", []):
            # Skip glob patterns
            if "*" in src:
                continue
            if not src.endswith(".py") and not src.endswith(".yml"):
                continue

            src_id = f"src_{src.replace('/', '_').replace('.', '_')}"
            if src_id not in node_ids:
                continue

            for doc in coupling.get("docs", []):
                if "current/" in doc:
                    doc_name = Path(doc).stem
                    doc_id = f"doc_current_{doc_name}"
                elif doc == "docs/ONTOLOGY.yaml":
                    doc_id = "doc_ONTOLOGY"
                elif doc == "docs/GLOSSARY.md":
                    doc_id = "doc_GLOSSARY"
                elif "CORE_SYSTEMS" in doc:
                    doc_id = "doc_CORE_SYSTEMS"
                else:
                    continue

                if doc_id in node_ids:
                    links.append({"source": src_id, "target": doc_id, "type": link_type})

    # Add target -> current links
    for link in data.get("target_current_links", []):
        target = link.get("target", "")
        current = link.get("current", "")
        target_name = Path(target).stem
        current_name = Path(current).stem
        target_id = f"doc_target_{target_name}"
        current_id = f"doc_current_{current_name}"
        if target_id in node_ids and current_id in node_ids:
            links.append({"source": target_id, "target": current_id, "type": "implements"})

    # Add hierarchy links
    links.append({"source": "doc_CLAUDE", "target": "doc_CORE_SYSTEMS", "type": "hierarchy"})
    links.append(
        {"source": "doc_CORE_SYSTEMS", "target": "doc_ONTOLOGY", "type": "hierarchy"}
    )

    return {"nodes": nodes, "links": links}


def generate_html(data: dict) -> str:
    """Generate HTML with embedded graph data."""
    graph_data = build_graph_data(data)
    json_data = json.dumps(graph_data, indent=2)
    return HTML_TEMPLATE.replace("GRAPH_DATA_PLACEHOLDER", json_data)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate interactive doc graph HTML")
    parser.add_argument("-o", "--output", default="doc_graph.html", help="Output file path")
    parser.add_argument("--serve", action="store_true", help="Open in browser after generating")
    args = parser.parse_args()

    data = load_relationships()
    html = generate_html(data)

    output_path = Path(args.output)
    with open(output_path, "w") as f:
        f.write(html)

    print(f"Generated: {output_path.absolute()}")

    if args.serve:
        webbrowser.open(f"file://{output_path.absolute()}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
