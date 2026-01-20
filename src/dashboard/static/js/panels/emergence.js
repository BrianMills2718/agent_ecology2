/**
 * Emergence Metrics panel - displays ecosystem emergence indicators (Plan #110 Phase 3)
 *
 * Shows metrics that help observe emergent organization patterns:
 * - Coordination density: How connected the agent network is
 * - Specialization index: How differentiated agents are
 * - Reuse ratio: Infrastructure building indicator
 * - Genesis independence: Ecosystem maturity
 * - Capital depth: Dependency chain length
 * - Coalition count: Number of distinct agent clusters
 */

const EmergencePanel = {
    elements: {
        toggle: null,
        content: null,
        panel: null,
        metricsGrid: null,
        specializationChart: null
    },

    isCollapsed: true,
    refreshInterval: null,
    chart: null,

    /**
     * Initialize the emergence panel
     */
    init() {
        this.elements.toggle = document.getElementById('emergence-toggle');
        this.elements.content = document.getElementById('emergence-content');
        this.elements.panel = document.querySelector('.emergence-panel');
        this.elements.metricsGrid = document.getElementById('emergence-metrics-grid');
        this.elements.specializationChart = document.getElementById('emergence-specialization-chart');

        // Toggle collapse
        if (this.elements.toggle) {
            this.elements.toggle.addEventListener('click', () => this.toggleCollapse());
        }

        // Load initial data
        this.refresh();

        // Auto-refresh every 5 seconds when not collapsed
        this.refreshInterval = setInterval(() => {
            if (!this.isCollapsed) {
                this.refresh();
            }
        }, 5000);
    },

    /**
     * Toggle panel collapse
     */
    toggleCollapse() {
        this.isCollapsed = !this.isCollapsed;

        if (this.elements.panel) {
            this.elements.panel.classList.toggle('collapsed', this.isCollapsed);
        }

        const icon = this.elements.toggle?.querySelector('.collapse-icon');
        if (icon) {
            icon.textContent = this.isCollapsed ? '+' : 'x';
        }

        // Refresh when expanded
        if (!this.isCollapsed) {
            this.refresh();
        }
    },

    /**
     * Refresh data from API
     */
    async refresh() {
        try {
            const response = await fetch('/api/emergence');
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            const metrics = await response.json();
            this.render(metrics);
        } catch (error) {
            console.error('Failed to load emergence metrics:', error);
            this.renderError(error.message);
        }
    },

    /**
     * Render metrics data
     */
    render(metrics) {
        if (!this.elements.metricsGrid) return;

        // Build metrics display
        const html = `
            <div class="emergence-metric">
                <div class="metric-label" title="How connected the agent network is (unique agent pairs / possible pairs)">
                    Coordination Density
                </div>
                <div class="metric-value">${this.formatPercent(metrics.coordination_density)}</div>
                <div class="metric-bar">
                    <div class="metric-bar-fill" style="width: ${Math.min(100, metrics.coordination_density * 100)}%"></div>
                </div>
            </div>

            <div class="emergence-metric">
                <div class="metric-label" title="How specialized agents are (coefficient of variation of action distributions)">
                    Specialization Index
                </div>
                <div class="metric-value">${metrics.specialization_index.toFixed(2)}</div>
                <div class="metric-bar">
                    <div class="metric-bar-fill specialization" style="width: ${Math.min(100, metrics.specialization_index * 50)}%"></div>
                </div>
            </div>

            <div class="emergence-metric">
                <div class="metric-label" title="Ratio of artifacts used by non-owners (infrastructure building)">
                    Reuse Ratio
                </div>
                <div class="metric-value">${this.formatPercent(metrics.reuse_ratio)}</div>
                <div class="metric-bar">
                    <div class="metric-bar-fill reuse" style="width: ${metrics.reuse_ratio * 100}%"></div>
                </div>
            </div>

            <div class="emergence-metric">
                <div class="metric-label" title="Non-genesis operations / total operations (ecosystem maturity)">
                    Genesis Independence
                </div>
                <div class="metric-value">${this.formatPercent(metrics.genesis_independence)}</div>
                <div class="metric-bar">
                    <div class="metric-bar-fill independence" style="width: ${metrics.genesis_independence * 100}%"></div>
                </div>
            </div>

            <div class="emergence-metric">
                <div class="metric-label" title="Maximum dependency chain length (capital structure depth)">
                    Capital Depth
                </div>
                <div class="metric-value">${metrics.capital_depth}</div>
                <div class="metric-bar">
                    <div class="metric-bar-fill depth" style="width: ${Math.min(100, metrics.capital_depth * 20)}%"></div>
                </div>
            </div>

            <div class="emergence-metric">
                <div class="metric-label" title="Number of distinct agent interaction clusters (coalitions)">
                    Coalition Count
                </div>
                <div class="metric-value">${metrics.coalition_count}</div>
                <div class="metric-sublabel">of ${metrics.agent_count} agents</div>
            </div>

            <div class="emergence-stats">
                <div class="stat-item">
                    <span class="stat-label">Total Interactions:</span>
                    <span class="stat-value">${metrics.total_interactions}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Genesis Invocations:</span>
                    <span class="stat-value">${metrics.genesis_invocations}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Non-Genesis Invocations:</span>
                    <span class="stat-value">${metrics.non_genesis_invocations}</span>
                </div>
                <div class="stat-item">
                    <span class="stat-label">Total Artifacts:</span>
                    <span class="stat-value">${metrics.total_artifacts}</span>
                </div>
            </div>
        `;

        this.elements.metricsGrid.innerHTML = html;

        // Render specialization chart if we have agent data
        if (this.elements.specializationChart && metrics.agent_specializations) {
            this.renderSpecializationChart(metrics.agent_specializations);
        }
    },

    /**
     * Render specialization breakdown chart
     */
    renderSpecializationChart(agentSpecializations) {
        const canvas = this.elements.specializationChart;
        if (!canvas) return;

        // Aggregate action types across all agents
        const actionTypeCounts = {};
        for (const [agentId, actions] of Object.entries(agentSpecializations)) {
            for (const [actionType, count] of Object.entries(actions)) {
                actionTypeCounts[actionType] = (actionTypeCounts[actionType] || 0) + count;
            }
        }

        const labels = Object.keys(actionTypeCounts);
        const data = Object.values(actionTypeCounts);

        // Destroy existing chart
        if (this.chart) {
            this.chart.destroy();
        }

        // Create new chart
        const ctx = canvas.getContext('2d');
        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: data,
                    backgroundColor: [
                        '#4CAF50', '#2196F3', '#FF9800', '#9C27B0',
                        '#00BCD4', '#E91E63', '#8BC34A', '#FFC107',
                        '#673AB7', '#03A9F4'
                    ]
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#e0e0e0',
                            font: { size: 10 }
                        }
                    },
                    title: {
                        display: true,
                        text: 'Action Type Distribution',
                        color: '#e0e0e0'
                    }
                }
            }
        });
    },

    /**
     * Render error state
     */
    renderError(message = '') {
        if (!this.elements.metricsGrid) return;
        const detail = message ? `<div class="error-detail">${message}</div>` : '';
        this.elements.metricsGrid.innerHTML = `
            <div class="emergence-error">
                Failed to load emergence metrics
                ${detail}
            </div>
        `;
    },

    /**
     * Format as percentage
     */
    formatPercent(value) {
        return (value * 100).toFixed(1) + '%';
    },

    /**
     * Cleanup
     */
    destroy() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
        }
        if (this.chart) {
            this.chart.destroy();
        }
    }
};

window.EmergencePanel = EmergencePanel;
