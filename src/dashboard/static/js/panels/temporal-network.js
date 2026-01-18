/**
 * Temporal Artifact Network Panel
 *
 * Visualizes ALL artifacts (agents, contracts, data) and their interactions over time.
 * Features:
 * - Artifact-centric view (everything is an artifact)
 * - Temporal playback with play/pause controls
 * - Activity heatmap showing intensity by tick
 * - Multiple edge types (invocation, dependency, ownership)
 */

const TemporalNetworkPanel = {
    network: null,
    nodes: null,
    edges: null,
    data: null,

    // Playback state
    isPlaying: false,
    playbackSpeed: 500, // ms per tick
    currentTick: 0,
    minTick: 0,
    maxTick: 0,
    playbackInterval: null,

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
        dependency: '#2196f3',
        ownership: '#9c27b0',
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
        this.heatmapContainer = document.getElementById('temporal-heatmap');
        this.slider = document.getElementById('temporal-tick-slider');
        this.sliderValue = document.getElementById('temporal-tick-value');
        this.playBtn = document.getElementById('temporal-play-btn');
        this.speedSelect = document.getElementById('temporal-speed');
        this.statsEl = document.getElementById('temporal-stats');

        if (!this.container) return;

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
                    damping: 0.4,
                },
                stabilization: {
                    iterations: 150,
                    fit: true,
                },
            },
            interaction: {
                hover: true,
                tooltipDelay: 100,
                zoomView: true,
                dragView: true,
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

        // Control event handlers
        if (this.slider) {
            this.slider.addEventListener('input', () => this.onSliderChange());
        }

        if (this.playBtn) {
            this.playBtn.addEventListener('click', () => this.togglePlayback());
        }

        if (this.speedSelect) {
            this.speedSelect.addEventListener('change', () => {
                this.playbackSpeed = parseInt(this.speedSelect.value);
                if (this.isPlaying) {
                    this.stopPlayback();
                    this.startPlayback();
                }
            });
        }

        // Initial load
        this.loadData();
    },

    async loadData() {
        try {
            const response = await fetch('/api/temporal-network');
            this.data = await response.json();

            // Set tick range
            [this.minTick, this.maxTick] = this.data.tick_range;
            this.currentTick = this.maxTick;

            // Update controls
            this.updateSliderRange();
            this.updateStats();

            // Render full graph
            this.renderGraph(this.maxTick);

            // Render heatmap
            this.renderHeatmap();
        } catch (err) {
            console.error('Failed to load temporal network data:', err);
        }
    },

    renderGraph(upToTick) {
        if (!this.data) return;

        // Clear existing
        this.nodes.clear();
        this.edges.clear();

        // Add all nodes (artifacts exist regardless of tick)
        const nodeData = this.data.nodes.map(node => ({
            id: node.id,
            label: node.label,
            shape: this.nodeShapes[node.artifact_type] || 'dot',
            color: this.getNodeColor(node),
            title: this.getNodeTooltip(node),
            size: this.getNodeSize(node),
        }));
        this.nodes.add(nodeData);

        // Filter edges by tick and aggregate
        const edgeMap = new Map();
        for (const edge of this.data.edges) {
            // Include static edges (tick=0) and edges up to current tick
            if (edge.tick > upToTick && edge.tick !== 0) continue;

            const key = `${edge.from_id}->${edge.to_id}:${edge.edge_type}`;
            if (edgeMap.has(key)) {
                const existing = edgeMap.get(key);
                existing.weight += edge.weight;
                existing.count++;
            } else {
                edgeMap.set(key, {
                    from: edge.from_id,
                    to: edge.to_id,
                    type: edge.edge_type,
                    weight: edge.weight,
                    count: 1,
                    tick: edge.tick,
                    details: edge.details,
                });
            }
        }

        // Convert to vis.js edges
        const edgeData = Array.from(edgeMap.values()).map((edge, idx) => ({
            id: idx,
            from: edge.from,
            to: edge.to,
            color: { color: this.edgeColors[edge.type] || '#888' },
            width: Math.min(1 + Math.log(edge.count + 1) * 1.5, 6),
            title: `${edge.type}: ${edge.count}x\n${edge.details || ''}`,
            dashes: edge.type === 'dependency' ? [5, 5] : false,
        }));
        this.edges.add(edgeData);

        // Update tick display
        if (this.sliderValue) {
            this.sliderValue.textContent = upToTick >= this.maxTick
                ? `Tick: All (${this.maxTick})`
                : `Tick: ${upToTick}`;
        }
    },

    getNodeColor(node) {
        const baseColor = this.nodeColors[node.artifact_type] || this.nodeColors.unknown;

        // Adjust for agent status
        if (node.artifact_type === 'agent') {
            switch (node.status) {
                case 'frozen':
                    return { background: '#f44336', border: '#d32f2f' };
                case 'low_resources':
                    return { background: '#ff9800', border: '#f57c00' };
            }
        }

        return baseColor;
    },

    getNodeSize(node) {
        // Size based on invocation count (artifacts that are used more are bigger)
        const baseSize = 15;
        if (node.invocation_count > 0) {
            return baseSize + Math.min(Math.log(node.invocation_count + 1) * 5, 20);
        }
        // Agents are slightly larger by default
        if (node.artifact_type === 'agent') {
            return baseSize + 5;
        }
        return baseSize;
    },

    getNodeTooltip(node) {
        let html = `<strong>${node.label}</strong><br>`;
        html += `Type: ${node.artifact_type}<br>`;

        if (node.artifact_type === 'agent') {
            html += `Scrip: ${node.scrip}<br>`;
            html += `Status: ${node.status}`;
        } else {
            if (node.owner_id) {
                html += `Owner: ${node.owner_id}<br>`;
            }
            html += `Invocations: ${node.invocation_count}<br>`;
            html += `Executable: ${node.executable ? 'Yes' : 'No'}`;
        }

        return html;
    },

    renderHeatmap() {
        if (!this.heatmapContainer || !this.data) return;

        const activity = this.data.activity_by_tick;
        if (Object.keys(activity).length === 0) {
            this.heatmapContainer.innerHTML = '<div class="no-data">No activity data</div>';
            return;
        }

        // Get all unique actors
        const actors = new Set();
        for (const tickData of Object.values(activity)) {
            for (const actor of Object.keys(tickData)) {
                actors.add(actor);
            }
        }
        const actorList = Array.from(actors).sort();

        // Find max activity for color scaling
        let maxActivity = 1;
        for (const tickData of Object.values(activity)) {
            for (const count of Object.values(tickData)) {
                maxActivity = Math.max(maxActivity, count);
            }
        }

        // Build heatmap HTML
        let html = '<div class="heatmap-grid">';

        // Header row (ticks)
        html += '<div class="heatmap-row header">';
        html += '<div class="heatmap-label"></div>';
        for (let tick = this.minTick; tick <= this.maxTick; tick++) {
            html += `<div class="heatmap-cell tick-header" data-tick="${tick}">${tick}</div>`;
        }
        html += '</div>';

        // Actor rows
        for (const actor of actorList) {
            html += '<div class="heatmap-row">';
            html += `<div class="heatmap-label" title="${actor}">${this.truncateLabel(actor)}</div>`;

            for (let tick = this.minTick; tick <= this.maxTick; tick++) {
                const count = (activity[tick] && activity[tick][actor]) || 0;
                const intensity = count / maxActivity;
                const bgColor = this.getHeatmapColor(intensity);

                html += `<div class="heatmap-cell"
                    data-tick="${tick}"
                    data-actor="${actor}"
                    style="background-color: ${bgColor}"
                    title="${actor}: ${count} actions at tick ${tick}"
                    onclick="TemporalNetworkPanel.jumpToTick(${tick})"
                ></div>`;
            }
            html += '</div>';
        }

        html += '</div>';
        this.heatmapContainer.innerHTML = html;
    },

    getHeatmapColor(intensity) {
        if (intensity === 0) return 'transparent';
        // Green gradient from light to dark
        const r = Math.round(76 - intensity * 40);
        const g = Math.round(175 - intensity * 50);
        const b = Math.round(80 - intensity * 40);
        const a = 0.3 + intensity * 0.7;
        return `rgba(${r}, ${g}, ${b}, ${a})`;
    },

    truncateLabel(label, maxLen = 8) {
        if (label.length <= maxLen) return label;
        return label.substring(0, maxLen - 2) + '..';
    },

    updateSliderRange() {
        if (!this.slider) return;

        this.slider.min = this.minTick;
        this.slider.max = this.maxTick;
        this.slider.value = this.maxTick;
    },

    updateStats() {
        if (!this.statsEl || !this.data) return;

        this.statsEl.innerHTML = `
            <span>Artifacts: ${this.data.total_artifacts}</span>
            <span>Interactions: ${this.data.total_interactions}</span>
        `;
    },

    onSliderChange() {
        const value = parseInt(this.slider.value);
        this.currentTick = value;
        this.renderGraph(value);
        this.highlightHeatmapTick(value);
    },

    jumpToTick(tick) {
        this.currentTick = tick;
        if (this.slider) {
            this.slider.value = tick;
        }
        this.renderGraph(tick);
        this.highlightHeatmapTick(tick);

        // Stop playback if playing
        if (this.isPlaying) {
            this.stopPlayback();
        }
    },

    highlightHeatmapTick(tick) {
        // Remove existing highlights
        document.querySelectorAll('.heatmap-cell.highlighted').forEach(el => {
            el.classList.remove('highlighted');
        });

        // Add highlight to current tick column
        document.querySelectorAll(`.heatmap-cell[data-tick="${tick}"]`).forEach(el => {
            el.classList.add('highlighted');
        });
    },

    togglePlayback() {
        if (this.isPlaying) {
            this.stopPlayback();
        } else {
            this.startPlayback();
        }
    },

    startPlayback() {
        this.isPlaying = true;
        if (this.playBtn) {
            this.playBtn.textContent = '⏸';
            this.playBtn.title = 'Pause';
        }

        // Reset to start if at end
        if (this.currentTick >= this.maxTick) {
            this.currentTick = this.minTick;
        }

        this.playbackInterval = setInterval(() => {
            this.currentTick++;

            if (this.currentTick > this.maxTick) {
                this.stopPlayback();
                this.currentTick = this.maxTick;
            }

            if (this.slider) {
                this.slider.value = this.currentTick;
            }
            this.renderGraph(this.currentTick);
            this.highlightHeatmapTick(this.currentTick);
        }, this.playbackSpeed);
    },

    stopPlayback() {
        this.isPlaying = false;
        if (this.playBtn) {
            this.playBtn.textContent = '▶';
            this.playBtn.title = 'Play';
        }

        if (this.playbackInterval) {
            clearInterval(this.playbackInterval);
            this.playbackInterval = null;
        }
    },

    onNodeClick(nodeId) {
        // Try to show artifact or agent detail
        if (typeof ArtifactsPanel !== 'undefined' && ArtifactsPanel.showArtifactModal) {
            ArtifactsPanel.showArtifactModal(nodeId);
        } else if (typeof AgentsPanel !== 'undefined' && AgentsPanel.showAgentModal) {
            AgentsPanel.showAgentModal(nodeId);
        }
    },

    // Called when new events arrive via WebSocket
    refresh() {
        // Only auto-refresh if not playing and showing all ticks
        if (!this.isPlaying && this.currentTick >= this.maxTick) {
            this.loadData();
        }
    },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    TemporalNetworkPanel.init();
});
