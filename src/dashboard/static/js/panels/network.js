/**
 * Network Graph Panel - Visualizes agent interactions
 */

const NetworkPanel = {
    network: null,
    nodes: null,
    edges: null,
    edgeMetadata: new Map(),  // Store edge metadata for click handling
    currentTick: null,
    maxTick: 100,

    // Edge colors by interaction type
    edgeColors: {
        scrip_transfer: '#4caf50',
        escrow_trade: '#2196f3',
        ownership_transfer: '#9c27b0',
        artifact_invoke: '#ff9800',
        genesis_invoke: '#00bcd4',  // Cyan for genesis artifact invocations
    },

    init() {
        this.container = document.getElementById('network-container');
        this.slider = document.getElementById('tick-slider');
        this.sliderValue = document.getElementById('tick-slider-value');

        if (!this.container) return;

        // Initialize vis.js datasets
        this.nodes = new vis.DataSet([]);
        this.edges = new vis.DataSet([]);

        // Network options
        const options = {
            nodes: {
                shape: 'dot',
                size: 20,
                font: {
                    size: 12,
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
                    roundness: 0.2,
                },
                shadow: true,
            },
            physics: {
                enabled: true,
                solver: 'forceAtlas2Based',
                forceAtlas2Based: {
                    gravitationalConstant: -50,
                    centralGravity: 0.01,
                    springLength: 100,
                    springConstant: 0.08,
                },
                stabilization: {
                    iterations: 100,
                },
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
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
                const nodeId = params.nodes[0];
                this.onNodeClick(nodeId);
            } else if (params.edges.length > 0) {
                const edgeId = params.edges[0];
                this.onEdgeClick(edgeId);
            }
        });

        this.network.on('hoverNode', (params) => {
            this.container.style.cursor = 'pointer';
        });

        this.network.on('blurNode', () => {
            this.container.style.cursor = 'default';
        });

        this.network.on('hoverEdge', (params) => {
            this.container.style.cursor = 'pointer';
        });

        this.network.on('blurEdge', () => {
            this.container.style.cursor = 'default';
        });

        // Slider event
        if (this.slider) {
            this.slider.addEventListener('input', () => {
                this.onSliderChange();
            });
        }

        // Initial load
        this.loadData();
    },

    async loadData(tickMax = null) {
        try {
            const url = tickMax !== null ? `/api/network?tick_max=${tickMax}` : '/api/network';
            const response = await fetch(url);
            const data = await response.json();

            this.updateGraph(data);
            this.updateSlider(data.tick_range);
        } catch (err) {
            console.error('Failed to load network data:', err);
        }
    },

    updateGraph(data) {
        // Clear existing data
        this.nodes.clear();
        this.edges.clear();
        this.edgeMetadata.clear();

        // Add nodes
        const nodeData = data.nodes.map(node => ({
            id: node.id,
            label: node.label,
            color: this.getNodeColor(node),
            title: this.getNodeTooltip(node),
        }));
        this.nodes.add(nodeData);

        // Add edges (aggregate by from/to/type)
        const edgeMap = new Map();
        for (const edge of data.edges) {
            const key = `${edge.from_id}->${edge.to_id}:${edge.interaction_type}`;
            if (edgeMap.has(key)) {
                const existing = edgeMap.get(key);
                existing.weight += edge.weight;
                existing.count++;
            } else {
                edgeMap.set(key, {
                    from: edge.from_id,
                    to: edge.to_id,
                    type: edge.interaction_type,
                    weight: edge.weight,
                    count: 1,
                    tick: edge.tick,
                });
            }
        }

        // Convert to vis.js edges and store metadata
        const edgeData = Array.from(edgeMap.values()).map((edge, idx) => {
            // Store metadata for click handling
            this.edgeMetadata.set(idx, {
                from: edge.from,
                to: edge.to,
                type: edge.type,
                count: edge.count,
            });

            return {
                id: idx,
                from: edge.from,
                to: edge.to,
                color: { color: this.edgeColors[edge.type] || '#888' },
                width: Math.min(1 + Math.log(edge.count + 1) * 2, 8),
                title: `${edge.type}: ${edge.count} interaction(s) (click for details)`,
            };
        });
        this.edges.add(edgeData);

        // Fit the network to view
        if (nodeData.length > 0) {
            this.network.fit({ animation: true });
        }
    },

    getNodeColor(node) {
        if (node.node_type === 'genesis') {
            return {
                background: '#0f4c75',
                border: '#00a8cc',
            };
        }

        // Color by status
        switch (node.status) {
            case 'frozen':
                return { background: '#f44336', border: '#d32f2f' };
            case 'low_resources':
                return { background: '#ff9800', border: '#f57c00' };
            default:
                return { background: '#4caf50', border: '#388e3c' };
        }
    },

    getNodeTooltip(node) {
        let html = `<strong>${node.label}</strong><br>`;
        html += `Type: ${node.node_type}<br>`;
        if (node.node_type === 'agent') {
            html += `Scrip: ${node.scrip}<br>`;
            html += `Status: ${node.status}`;
        }
        return html;
    },

    updateSlider(tickRange) {
        if (!this.slider) return;

        const [minTick, maxTick] = tickRange;
        this.maxTick = maxTick || 100;

        this.slider.min = 0;
        this.slider.max = this.maxTick;
        this.slider.value = this.maxTick;
        this.sliderValue.textContent = 'Tick: All';
    },

    onSliderChange() {
        const value = parseInt(this.slider.value);
        if (value >= this.maxTick) {
            this.sliderValue.textContent = 'Tick: All';
            this.loadData(null);
        } else {
            this.sliderValue.textContent = `Tick: ${value}`;
            this.loadData(value);
        }
    },

    onNodeClick(nodeId) {
        // Show agent modal if it's an agent
        if (typeof AgentsPanel !== 'undefined' && AgentsPanel.showAgentModal) {
            AgentsPanel.showAgentModal(nodeId);
        }
    },

    async onEdgeClick(edgeId) {
        // Get edge metadata
        const metadata = this.edgeMetadata.get(edgeId);
        if (!metadata) return;

        const { from, to } = metadata;

        try {
            // Fetch pairwise interactions from API
            const response = await fetch(`/api/agents/interactions?from_agent=${encodeURIComponent(from)}&to_agent=${encodeURIComponent(to)}`);
            const data = await response.json();

            // Show the interaction modal
            this.showInteractionModal(data);
        } catch (err) {
            console.error('Failed to load interaction data:', err);
        }
    },

    showInteractionModal(data) {
        // Get or create modal
        let modal = document.getElementById('interaction-modal');
        if (!modal) {
            modal = this.createInteractionModal();
            document.body.appendChild(modal);
        }

        // Populate modal
        const title = modal.querySelector('#interaction-modal-title');
        const summary = modal.querySelector('#interaction-modal-summary');
        const list = modal.querySelector('#interaction-modal-list');

        title.textContent = `${data.from_agent} <-> ${data.to_agent}`;

        // Build summary
        let summaryHtml = `
            <div class="interaction-stat">
                <span class="stat-label">Total Interactions:</span>
                <span class="stat-value">${data.total_count}</span>
            </div>
            <div class="interaction-stat">
                <span class="stat-label">Direction:</span>
                <span class="stat-value">${data.bidirectional ? 'Bidirectional' : 'One-way'}</span>
            </div>
        `;

        if (data.scrip_transfers > 0) {
            summaryHtml += `
                <div class="interaction-stat">
                    <span class="stat-label">Scrip Transfers:</span>
                    <span class="stat-value">${data.scrip_transfers} (${data.scrip_total} total)</span>
                </div>
            `;
        }
        if (data.escrow_trades > 0) {
            summaryHtml += `
                <div class="interaction-stat">
                    <span class="stat-label">Escrow Trades:</span>
                    <span class="stat-value">${data.escrow_trades}</span>
                </div>
            `;
        }
        if (data.artifact_invocations > 0) {
            summaryHtml += `
                <div class="interaction-stat">
                    <span class="stat-label">Artifact Invocations:</span>
                    <span class="stat-value">${data.artifact_invocations}</span>
                </div>
            `;
        }
        if (data.genesis_invocations > 0) {
            summaryHtml += `
                <div class="interaction-stat">
                    <span class="stat-label">Genesis Invocations:</span>
                    <span class="stat-value">${data.genesis_invocations}</span>
                </div>
            `;
        }
        summary.innerHTML = summaryHtml;

        // Build interaction list (most recent first)
        const interactions = [...data.interactions].reverse().slice(0, 50);
        list.innerHTML = interactions.map(i => `
            <div class="interaction-item ${i.interaction_type}">
                <div class="interaction-header">
                    <span class="interaction-type">${i.interaction_type.replace(/_/g, ' ')}</span>
                    <span class="interaction-tick">Tick ${i.tick}</span>
                </div>
                <div class="interaction-details">
                    <span class="interaction-direction">${i.from_id} -> ${i.to_id}</span>
                    ${i.amount ? `<span class="interaction-amount">${i.amount} scrip</span>` : ''}
                    ${i.artifact_id ? `<span class="interaction-artifact">${i.artifact_id}</span>` : ''}
                </div>
                ${i.details ? `<div class="interaction-description">${i.details}</div>` : ''}
            </div>
        `).join('');

        // Show modal
        modal.classList.remove('hidden');
    },

    createInteractionModal() {
        const modal = document.createElement('div');
        modal.id = 'interaction-modal';
        modal.className = 'modal hidden';
        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2 id="interaction-modal-title">Interactions</h2>
                    <button class="modal-close" id="interaction-modal-close">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="modal-section">
                        <h3>Summary</h3>
                        <div class="interaction-summary" id="interaction-modal-summary">
                        </div>
                    </div>
                    <div class="modal-section">
                        <h3>Recent Interactions</h3>
                        <div class="interaction-list scrollable" id="interaction-modal-list">
                        </div>
                    </div>
                </div>
            </div>
        `;

        // Close button handler
        modal.querySelector('#interaction-modal-close').addEventListener('click', () => {
            modal.classList.add('hidden');
        });

        // Click outside to close
        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.classList.add('hidden');
            }
        });

        return modal;
    },

    // Called when new events arrive via WebSocket
    refresh() {
        // Only refresh if showing "all" ticks
        if (this.slider && parseInt(this.slider.value) >= this.maxTick) {
            this.loadData(null);
        }
    },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    NetworkPanel.init();
});
