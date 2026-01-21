/**
 * World Configuration panel - displays simulation settings
 */

const ConfigPanel = {
    elements: {
        toggle: null,
        content: null,
        grid: null,
        panel: null
    },

    isCollapsed: true,

    /**
     * Initialize the config panel
     */
    init() {
        this.elements.toggle = document.getElementById('config-toggle');
        this.elements.content = document.getElementById('config-content');
        this.elements.grid = document.getElementById('config-grid');
        this.elements.panel = document.querySelector('.config-panel');

        // Toggle collapse
        if (this.elements.toggle) {
            this.elements.toggle.addEventListener('click', () => this.toggleCollapse());
        }

        // Load config on init
        this.load();
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
            icon.textContent = this.isCollapsed ? '▼' : '▲';
        }
    },

    /**
     * Load configuration from API
     */
    async load() {
        try {
            const response = await fetch('/api/config');
            const config = await response.json();
            this.render(config);
        } catch (error) {
            console.error('Failed to load config:', error);
            if (this.elements.grid) {
                this.elements.grid.innerHTML = '<div class="config-section"><p>Failed to load configuration</p></div>';
            }
        }
    },

    /**
     * Render configuration data
     */
    render(config) {
        if (!this.elements.grid) return;

        let html = '';

        // World settings
        if (config.world) {
            html += '<div class="config-section"><h4>World</h4>' +
                this.renderItems({
                    'Max Ticks': config.world.max_ticks,
                    'Autonomous Mode': config.world.use_autonomous_loops ? 'Yes' : 'No'
                }) + '</div>';
        }

        // Resource settings
        if (config.resources) {
            const flow = config.resources.flow || {};
            const stock = config.resources.stock || {};
            html += '<div class="config-section"><h4>Resources (Flow)</h4>' +
                this.renderItems({
                    'LLM Tokens Quota': flow.compute?.per_tick || 'N/A',
                    'LLM Rate': flow.llm_rate?.per_minute || 'N/A'
                }) + '</div>' +
                '<div class="config-section"><h4>Resources (Stock)</h4>' +
                this.renderItems({
                    'Disk Quota': stock.disk?.default_quota || 'N/A',
                    'Memory Quota': stock.memory?.default_quota || 'N/A'
                }) + '</div>';
        }

        // Cost settings
        if (config.costs) {
            html += '<div class="config-section"><h4>Token Costs</h4>' +
                this.renderItems({
                    'Input (per 1K)': config.costs.per_1k_input_tokens || 1,
                    'Output (per 1K)': config.costs.per_1k_output_tokens || 3
                }) + '</div>';
        }

        // Budget settings
        if (config.budget) {
            html += '<div class="config-section"><h4>Budget</h4>' +
                this.renderItems({
                    'Max API Cost': '$' + (config.budget.max_api_cost || 1.00).toFixed(2),
                    'Checkpoint Interval': config.budget.checkpoint_interval || 10
                }) + '</div>';
        }

        // Genesis artifacts
        if (config.genesis) {
            const enabled = [];
            if (config.genesis.ledger?.enabled !== false) enabled.push('Ledger');
            if (config.genesis.mint?.enabled !== false) enabled.push('Mint');
            if (config.genesis.escrow?.enabled !== false) enabled.push('Escrow');
            if (config.genesis.store?.enabled !== false) enabled.push('Store');

            html += '<div class="config-section"><h4>Genesis Artifacts</h4>' +
                this.renderItems({
                    'Enabled': enabled.join(', ') || 'None'
                }) + '</div>';
        }

        this.elements.grid.innerHTML = html || '<div class="config-section"><p>No configuration available</p></div>';
    },

    /**
     * Render key-value items
     */
    renderItems(items) {
        return Object.entries(items)
            .map(([key, value]) => '<div class="config-item">' +
                '<span class="config-label">' + key + '</span>' +
                '<span class="config-value">' + value + '</span>' +
                '</div>').join('');
    }
};

window.ConfigPanel = ConfigPanel;
