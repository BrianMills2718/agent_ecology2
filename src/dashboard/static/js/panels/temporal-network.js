/**
 * Temporal Artifact Network Panel
 *
 * Visualizes ALL artifacts (agents, contracts, data) and their interactions over time.
 * Features:
 * - Artifact-centric view (everything is an artifact)
 * - Temporal playback with play/pause controls
 * - Activity heatmap showing intensity by time window
 * - Multiple edge types (invocation, dependency, ownership)
 */

const TemporalNetworkPanel = {
    network: null,
    nodes: null,
    edges: null,
    data: null,

    // Playback state
    isPlaying: false,
    playbackSpeed: 500, // ms per time step
    currentTimeIndex: 0,
    timeBuckets: [], // Sorted array of time bucket keys
    playbackInterval: null,

    // Time range
    timeStart: null,
    timeEnd: null,

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

            // Parse time range
            [this.timeStart, this.timeEnd] = this.data.time_range;

            // Extract and sort time buckets for playback
            this.timeBuckets = Object.keys(this.data.activity_by_time).sort();

            // Set current position to end
            this.currentTimeIndex = Math.max(0, this.timeBuckets.length - 1);

            // Update controls
            this.updateSliderRange();
            this.updateStats();

            // Render full graph (all edges)
            this.renderGraph(null); // null = show all

            // Render heatmap
            this.renderHeatmap();
        } catch (err) {
            console.error('Failed to load temporal network data:', err);
        }
    },

    /**
     * Format timestamp for display
     * @param {string} timestamp - ISO timestamp
     * @param {boolean} showDate - Whether to include date
     */
    formatTime(timestamp, showDate = false) {
        if (!timestamp) return 'N/A';
        try {
            const date = new Date(timestamp);
            if (showDate) {
                return date.toLocaleString();
            }
            return date.toLocaleTimeString();
        } catch (e) {
            return timestamp;
        }
    },

    /**
     * Get elapsed time from simulation start
     * @param {string} timestamp - ISO timestamp
     */
    getElapsedTime(timestamp) {
        if (!timestamp || !this.timeStart) return '';
        try {
            const current = new Date(timestamp);
            const start = new Date(this.timeStart);
            const diffMs = current - start;
            const seconds = Math.floor(diffMs / 1000);
            const minutes = Math.floor(seconds / 60);
            const hours = Math.floor(minutes / 60);

            if (hours > 0) {
                return `${hours}h ${minutes % 60}m ${seconds % 60}s`;
            } else if (minutes > 0) {
                return `${minutes}m ${seconds % 60}s`;
            } else {
                return `${seconds}s`;
            }
        } catch (e) {
            return '';
        }
    },

    renderGraph(upToTimestamp) {
        if (!this.data) return;

        // Clear existing
        this.nodes.clear();
        this.edges.clear();

        // Add all nodes (artifacts exist regardless of time)
        const nodeData = this.data.nodes.map(node => ({
            id: node.id,
            label: node.label,
            shape: this.nodeShapes[node.artifact_type] || 'dot',
            color: this.getNodeColor(node),
            title: this.getNodeTooltip(node),
            size: this.getNodeSize(node),
        }));
        this.nodes.add(nodeData);

        // Filter edges by timestamp and aggregate
        const edgeMap = new Map();
        for (const edge of this.data.edges) {
            // Static edges (no timestamp) are always included
            // Dynamic edges are included if before upToTimestamp (or upToTimestamp is null = show all)
            if (edge.timestamp && upToTimestamp) {
                if (edge.timestamp > upToTimestamp) continue;
            }

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
                    timestamp: edge.timestamp,
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

        // Update time display
        if (this.sliderValue) {
            if (upToTimestamp === null || this.currentTimeIndex >= this.timeBuckets.length - 1) {
                this.sliderValue.textContent = `Time: All (${this.getElapsedTime(this.timeEnd)})`;
            } else {
                const elapsed = this.getElapsedTime(upToTimestamp);
                this.sliderValue.textContent = `Time: +${elapsed}`;
            }
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
            if (node.created_at) {
                html += `<br>Created: ${this.formatTime(node.created_at, true)}`;
            }
        }

        return html;
    },

    renderHeatmap() {
        if (!this.heatmapContainer || !this.data) return;

        const activity = this.data.activity_by_time;
        if (Object.keys(activity).length === 0) {
            this.heatmapContainer.innerHTML = '<div class="no-data">No activity data</div>';
            return;
        }

        // Get all unique actors
        const actors = new Set();
        for (const timeData of Object.values(activity)) {
            for (const actor of Object.keys(timeData)) {
                actors.add(actor);
            }
        }
        const actorList = Array.from(actors).sort();

        // Sort time buckets
        const sortedBuckets = Object.keys(activity).sort();

        // Find max activity for color scaling
        let maxActivity = 1;
        for (const timeData of Object.values(activity)) {
            for (const count of Object.values(timeData)) {
                maxActivity = Math.max(maxActivity, count);
            }
        }

        // Build heatmap HTML
        let html = '<div class="heatmap-grid">';

        // Header row (time buckets)
        html += '<div class="heatmap-row header">';
        html += '<div class="heatmap-label"></div>';
        for (let i = 0; i < sortedBuckets.length; i++) {
            const bucket = sortedBuckets[i];
            const elapsed = this.getElapsedTime(bucket);
            html += `<div class="heatmap-cell time-header" data-time-index="${i}" title="${this.formatTime(bucket, true)}">${elapsed || 'Start'}</div>`;
        }
        html += '</div>';

        // Actor rows
        for (const actor of actorList) {
            html += '<div class="heatmap-row">';
            html += `<div class="heatmap-label" title="${actor}">${this.truncateLabel(actor)}</div>`;

            for (let i = 0; i < sortedBuckets.length; i++) {
                const bucket = sortedBuckets[i];
                const count = (activity[bucket] && activity[bucket][actor]) || 0;
                const intensity = count / maxActivity;
                const bgColor = this.getHeatmapColor(intensity);

                html += `<div class="heatmap-cell"
                    data-time-index="${i}"
                    data-actor="${actor}"
                    style="background-color: ${bgColor}"
                    title="${actor}: ${count} actions at ${this.formatTime(bucket)}"
                    onclick="TemporalNetworkPanel.jumpToTimeIndex(${i})"
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

        this.slider.min = 0;
        this.slider.max = Math.max(0, this.timeBuckets.length - 1);
        this.slider.value = this.slider.max;
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
        this.currentTimeIndex = value;

        const timestamp = this.timeBuckets[value] || null;
        this.renderGraph(timestamp);
        this.highlightHeatmapTime(value);
    },

    jumpToTimeIndex(index) {
        this.currentTimeIndex = index;
        if (this.slider) {
            this.slider.value = index;
        }

        const timestamp = this.timeBuckets[index] || null;
        this.renderGraph(timestamp);
        this.highlightHeatmapTime(index);

        // Stop playback if playing
        if (this.isPlaying) {
            this.stopPlayback();
        }
    },

    highlightHeatmapTime(timeIndex) {
        // Remove existing highlights
        document.querySelectorAll('.heatmap-cell.highlighted').forEach(el => {
            el.classList.remove('highlighted');
        });

        // Add highlight to current time column
        document.querySelectorAll(`.heatmap-cell[data-time-index="${timeIndex}"]`).forEach(el => {
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
        if (this.timeBuckets.length === 0) return;

        this.isPlaying = true;
        if (this.playBtn) {
            this.playBtn.textContent = '⏸';
            this.playBtn.title = 'Pause';
        }

        // Reset to start if at end
        if (this.currentTimeIndex >= this.timeBuckets.length - 1) {
            this.currentTimeIndex = 0;
        }

        this.playbackInterval = setInterval(() => {
            this.currentTimeIndex++;

            if (this.currentTimeIndex >= this.timeBuckets.length) {
                this.stopPlayback();
                this.currentTimeIndex = this.timeBuckets.length - 1;
            }

            if (this.slider) {
                this.slider.value = this.currentTimeIndex;
            }

            const timestamp = this.timeBuckets[this.currentTimeIndex] || null;
            this.renderGraph(timestamp);
            this.highlightHeatmapTime(this.currentTimeIndex);
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
        // Only auto-refresh if not playing and showing all time
        if (!this.isPlaying && this.currentTimeIndex >= this.timeBuckets.length - 1) {
            this.loadData();
        }
    },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    TemporalNetworkPanel.init();
});
