/**
 * Temporal Network Panel (Plan #107)
 *
 * Visualizes ALL artifacts (agents, genesis, contracts, data) and their interactions.
 * Unlike the basic network panel, this includes genesis artifact invocations.
 */

const TemporalNetworkPanel = {
    network: null,
    nodes: null,
    edges: null,
    data: null,
    container: null,

    // Node colors by artifact type
    nodeColors: {
        agent: { background: '#4caf50', border: '#388e3c' },
        genesis: { background: '#0f4c75', border: '#00a8cc' },
        contract: { background: '#9c27b0', border: '#7b1fa2' },
        data: { background: '#607d8b', border: '#455a64' },
        unknown: { background: '#9e9e9e', border: '#757575' },
    },

    // Edge colors by type
    edgeColors: {
        invocation: '#ff9800',
        ownership: '#9c27b0',
        dependency: '#2196f3',
        creation: '#4caf50',
        transfer: '#f44336',
    },

    // Node shapes by artifact type
    nodeShapes: {
        agent: 'dot',
        genesis: 'star',
        contract: 'diamond',
        data: 'square',
        unknown: 'dot',
    },

    init() {
        this.container = document.getElementById('temporal-network-container');
        this.statsEl = document.getElementById('temporal-network-stats');
        this.legendEl = document.getElementById('temporal-network-legend');

        if (!this.container) {
            console.warn('Temporal network container not found');
            return;
        }

        // Initialize vis.js datasets
        this.nodes = new vis.DataSet([]);
        this.edges = new vis.DataSet([]);

        // Network options
        const options = {
            nodes: {
                size: 20,
                font: {
                    size: 11,
                    color: '#eaeaea',
                },
                borderWidth: 2,
                shadow: true,
            },
            edges: {
                width: 2,
                arrows: {
                    to: { enabled: true, scaleFactor: 0.5 },
                },
                smooth: {
                    type: 'curvedCW',
                    roundness: 0.15,
                },
                shadow: true,
            },
            physics: {
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -80,
                    centralGravity: 0.005,
                    springLength: 150,
                    springConstant: 0.05,
                    damping: 0.5,
                },
                stabilization: {
                    enabled: true,
                    iterations: 200,
                    updateInterval: 25,
                },
            },
            interaction: {
                hover: true,
                tooltipDelay: 200,
                hideEdgesOnDrag: true,
            },
            groups: this.buildGroups(),
        };

        // Create the network
        this.network = new vis.Network(
            this.container,
            { nodes: this.nodes, edges: this.edges },
            options
        );

        // Build legend
        this.buildLegend();

        // Load initial data
        this.refresh();
    },

    buildGroups() {
        const groups = {};
        for (const [type, colors] of Object.entries(this.nodeColors)) {
            groups[type] = {
                color: colors,
                shape: this.nodeShapes[type] || 'dot',
            };
        }
        return groups;
    },

    buildLegend() {
        if (!this.legendEl) return;

        let html = '<div class="legend-section"><strong>Nodes:</strong> ';
        for (const [type, colors] of Object.entries(this.nodeColors)) {
            html += `<span class="legend-item">
                <span class="legend-dot" style="background:${colors.background};border-color:${colors.border}"></span>
                ${type}
            </span>`;
        }
        html += '</div><div class="legend-section"><strong>Edges:</strong> ';
        for (const [type, color] of Object.entries(this.edgeColors)) {
            html += `<span class="legend-item">
                <span class="legend-line" style="background:${color}"></span>
                ${type}
            </span>`;
        }
        html += '</div>';
        this.legendEl.innerHTML = html;
    },

    async refresh() {
        try {
            const response = await fetch('/api/temporal-network');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            this.data = await response.json();
            this.updateGraph();
            this.updateStats();
        } catch (error) {
            console.error('Failed to fetch temporal network data:', error);
        }
    },

    updateGraph() {
        if (!this.data) return;

        // Clear existing data
        this.nodes.clear();
        this.edges.clear();

        // Add nodes
        const nodeData = this.data.nodes.map(node => ({
            id: node.id,
            label: this.formatLabel(node.label),
            title: this.buildNodeTooltip(node),
            group: node.artifact_type,
            value: node.invocation_count || 1,  // Size by invocations
        }));
        this.nodes.add(nodeData);

        // Add edges
        const edgeData = this.data.edges.map((edge, idx) => ({
            id: `edge-${idx}`,
            from: edge.from_id,
            to: edge.to_id,
            color: { color: this.edgeColors[edge.edge_type] || '#888' },
            width: Math.min(Math.log2(edge.weight + 1) * 2, 8),  // Scale width by weight
            title: edge.details || `${edge.edge_type}: ${edge.from_id} → ${edge.to_id}`,
            arrows: edge.edge_type === 'ownership' ? { to: false } : { to: true },
            dashes: edge.edge_type === 'ownership',  // Dashed for ownership
        }));
        this.edges.add(edgeData);

        // Fit to view
        if (this.network) {
            this.network.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
        }
    },

    formatLabel(label) {
        // Shorten long labels
        if (label.length > 20) {
            return label.substring(0, 17) + '...';
        }
        return label;
    },

    buildNodeTooltip(node) {
        let tooltip = `<strong>${node.id}</strong><br>`;
        tooltip += `Type: ${node.artifact_type}<br>`;
        if (node.created_by) {
            tooltip += `Owner: ${node.created_by}<br>`;
        }
        if (node.invocation_count > 0) {
            tooltip += `Invocations: ${node.invocation_count}<br>`;
        }
        if (node.scrip > 0) {
            tooltip += `Scrip: ${node.scrip}<br>`;
        }
        if (node.status && node.status !== 'active') {
            tooltip += `Status: ${node.status}<br>`;
        }
        return tooltip;
    },

    updateStats() {
        if (!this.statsEl || !this.data) return;

        const nodesByType = {};
        for (const node of this.data.nodes) {
            nodesByType[node.artifact_type] = (nodesByType[node.artifact_type] || 0) + 1;
        }

        const edgesByType = {};
        for (const edge of this.data.edges) {
            edgesByType[edge.edge_type] = (edgesByType[edge.edge_type] || 0) + 1;
        }

        let html = `<div class="stat-row">
            <span class="stat-label">Artifacts:</span>
            <span class="stat-value">${this.data.total_artifacts}</span>
        </div>`;

        for (const [type, count] of Object.entries(nodesByType)) {
            html += `<div class="stat-row">
                <span class="stat-label">&nbsp;&nbsp;${type}:</span>
                <span class="stat-value">${count}</span>
            </div>`;
        }

        html += `<div class="stat-row">
            <span class="stat-label">Interactions:</span>
            <span class="stat-value">${this.data.total_interactions}</span>
        </div>`;

        for (const [type, count] of Object.entries(edgesByType)) {
            html += `<div class="stat-row">
                <span class="stat-label">&nbsp;&nbsp;${type}:</span>
                <span class="stat-value">${count}</span>
            </div>`;
        }

        if (this.data.time_range[0]) {
            html += `<div class="stat-row">
                <span class="stat-label">Time range:</span>
                <span class="stat-value">${this.formatTime(this.data.time_range[0])}</span>
            </div>`;
        }

        this.statsEl.innerHTML = html;
    },

    formatTime(isoString) {
        if (!isoString) return 'N/A';
        try {
            const date = new Date(isoString);
            return date.toLocaleTimeString();
        } catch {
            return isoString;
        }
    },

    // Called when panel becomes visible
    onShow() {
        this.refresh();
        if (this.network) {
            this.network.redraw();
            this.network.fit();
        }
    },
};

// Export for use in main.js
window.TemporalNetworkPanel = TemporalNetworkPanel;
