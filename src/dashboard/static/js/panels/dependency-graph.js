/**
 * Dependency Graph Panel - Visualizes artifact capital structure
 * Plan #64: Artifact Dependency Graph Visualization
 *
 * Shows how artifacts depend on each other, revealing emergent capital chains.
 * This is pure observability - we don't define "good" structure, just make it visible.
 */

const DependencyGraphPanel = {
    network: null,
    nodes: null,
    edges: null,
    container: null,
    metrics: null,

    // Node colors by type
    nodeColors: {
        genesis: { background: '#ffd700', border: '#b8860b' },      // Gold for genesis
        contract: { background: '#4caf50', border: '#388e3c' },     // Green for contracts
        executable: { background: '#2196f3', border: '#1976d2' },   // Blue for executable
        data: { background: '#9c27b0', border: '#7b1fa2' },         // Purple for data
        default: { background: '#607d8b', border: '#455a64' },      // Gray for others
    },

    init() {
        this.container = document.getElementById('dependency-graph-container');
        this.metricsContainer = document.getElementById('dependency-metrics');
        this.filterSelect = document.getElementById('dependency-filter');

        if (!this.container) {
            console.warn('Dependency graph container not found');
            return;
        }

        // Initialize vis.js datasets
        this.nodes = new vis.DataSet([]);
        this.edges = new vis.DataSet([]);

        // Network options - hierarchical layout for dependency chains
        const options = {
            nodes: {
                shape: 'dot',
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
                color: { color: '#666', highlight: '#999' },
                smooth: {
                    type: 'cubicBezier',
                    forceDirection: 'vertical',
                    roundness: 0.4,
                },
            },
            layout: {
                hierarchical: {
                    enabled: true,
                    direction: 'UD',  // Up-Down (genesis at top)
                    sortMethod: 'directed',
                    levelSeparation: 80,
                    nodeSpacing: 120,
                },
            },
            physics: {
                enabled: false,  // Hierarchical layout handles positioning
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                navigationButtons: true,
                keyboard: true,
            },
        };

        // Create network
        this.network = new vis.Network(this.container, {
            nodes: this.nodes,
            edges: this.edges,
        }, options);

        // Event handlers
        this.network.on('click', (params) => {
            if (params.nodes.length > 0) {
                this.onNodeClick(params.nodes[0]);
            }
        });

        this.network.on('hoverNode', () => {
            this.container.style.cursor = 'pointer';
        });

        this.network.on('blurNode', () => {
            this.container.style.cursor = 'default';
        });

        // Filter handler
        if (this.filterSelect) {
            this.filterSelect.addEventListener('change', () => {
                this.loadData();
            });
        }

        // Initial load
        this.loadData();
    },

    async loadData() {
        try {
            const response = await fetch('/api/artifacts/dependency-graph');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }
            const data = await response.json();
            this.updateGraph(data);
            this.updateMetrics(data.metrics);
        } catch (err) {
            console.error('Failed to load dependency graph:', err);
            this.showError('Failed to load dependency graph');
        }
    },

    updateGraph(data) {
        // Clear existing data
        this.nodes.clear();
        this.edges.clear();

        // Get filter value
        const filter = this.filterSelect ? this.filterSelect.value : '';

        // Filter nodes based on selection
        let filteredNodes = data.nodes;
        if (filter === 'genesis') {
            filteredNodes = data.nodes.filter(n => n.is_genesis);
        } else if (filter === 'agent-created') {
            filteredNodes = data.nodes.filter(n => !n.is_genesis);
        } else if (filter === 'with-deps') {
            const nodeIds = new Set(data.nodes.map(n => n.id));
            const hasEdge = new Set();
            data.edges.forEach(e => {
                hasEdge.add(e.source);
                hasEdge.add(e.target);
            });
            filteredNodes = data.nodes.filter(n => hasEdge.has(n.id));
        }

        const filteredNodeIds = new Set(filteredNodes.map(n => n.id));

        // Add nodes
        const nodeData = filteredNodes.map(node => ({
            id: node.id,
            label: this.truncateLabel(node.id),
            color: this.getNodeColor(node),
            size: this.getNodeSize(node),
            title: this.getNodeTooltip(node),
            level: node.depth || 0,  // Use depth for hierarchical layout
        }));
        this.nodes.add(nodeData);

        // Add edges (only between filtered nodes)
        const edgeData = data.edges
            .filter(e => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target))
            .map((edge, idx) => ({
                id: idx,
                from: edge.source,
                to: edge.target,
                title: `${edge.source} depends on ${edge.target}`,
            }));
        this.edges.add(edgeData);

        // Fit view
        if (nodeData.length > 0) {
            setTimeout(() => this.network.fit({ animation: true }), 100);
        }
    },

    truncateLabel(label) {
        if (label.length > 15) {
            return label.substring(0, 12) + '...';
        }
        return label;
    },

    getNodeColor(node) {
        if (node.is_genesis) {
            return this.nodeColors.genesis;
        }
        if (node.type === 'contract') {
            return this.nodeColors.contract;
        }
        if (node.is_executable) {
            return this.nodeColors.executable;
        }
        if (node.type === 'data') {
            return this.nodeColors.data;
        }
        return this.nodeColors.default;
    },

    getNodeSize(node) {
        // Size by invocation count (Lindy effect proxy)
        const baseSize = 15;
        const invocations = node.invocation_count || 0;
        return baseSize + Math.min(Math.log(invocations + 1) * 5, 20);
    },

    getNodeTooltip(node) {
        let html = `<strong>${node.id}</strong><br>`;
        html += `Type: ${node.type || 'unknown'}<br>`;
        html += `Owner: ${node.owner || 'none'}<br>`;
        if (node.is_genesis) {
            html += `<em>Genesis artifact</em><br>`;
        }
        if (node.depth !== undefined) {
            html += `Depth: ${node.depth}<br>`;
        }
        if (node.invocation_count) {
            html += `Invocations: ${node.invocation_count}<br>`;
        }
        if (node.lindy_score) {
            html += `Lindy Score: ${node.lindy_score.toFixed(1)}`;
        }
        return html;
    },

    updateMetrics(metrics) {
        if (!this.metricsContainer || !metrics) return;

        this.metricsContainer.innerHTML = `
            <div class="metric">
                <span class="metric-label">Max Depth:</span>
                <span class="metric-value">${metrics.max_depth || 0}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Avg Fanout:</span>
                <span class="metric-value">${(metrics.avg_fanout || 0).toFixed(2)}</span>
            </div>
            <div class="metric">
                <span class="metric-label">Genesis Ratio:</span>
                <span class="metric-value">${((metrics.genesis_dependency_ratio || 0) * 100).toFixed(0)}%</span>
            </div>
            <div class="metric">
                <span class="metric-label">Orphans:</span>
                <span class="metric-value">${metrics.orphan_count || 0}</span>
            </div>
        `;
    },

    showError(message) {
        if (this.container) {
            this.container.innerHTML = `<div class="graph-error">${message}</div>`;
        }
    },

    onNodeClick(nodeId) {
        // Show artifact modal if available
        if (typeof ArtifactsPanel !== 'undefined' && ArtifactsPanel.showArtifactModal) {
            ArtifactsPanel.showArtifactModal(nodeId);
        }
    },

    // Called when new events arrive via WebSocket
    refresh() {
        this.loadData();
    },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    DependencyGraphPanel.init();
});
