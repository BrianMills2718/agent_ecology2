/**
 * Progress display panel
 */

const ProgressPanel = {
    elements: {
        tickDisplay: null,
        statusDisplay: null,
        tickProgress: null,
        budgetDisplay: null,
        budgetProgress: null,
        tpsDisplay: null
    },

    /**
     * Initialize the progress panel
     */
    init() {
        this.elements.tickDisplay = document.getElementById('tick-display');
        this.elements.statusDisplay = document.getElementById('status-display');
        this.elements.tickProgress = document.getElementById('tick-progress');
        this.elements.budgetDisplay = document.getElementById('budget-display');
        this.elements.budgetProgress = document.getElementById('budget-progress');
        this.elements.tpsDisplay = document.getElementById('tps-display');

        // Listen for state updates
        window.wsManager.on('state_update', (data) => {
            if (data.progress) {
                this.update(data.progress);
            }
        });

        window.wsManager.on('initial_state', (data) => {
            if (data.progress) {
                this.update(data.progress);
            }
        });
    },

    /**
     * Update progress display
     */
    update(progress) {
        if (!progress) return;

        // Tick progress
        const tickPercent = (progress.current_tick / progress.max_ticks) * 100;
        if (this.elements.tickDisplay) {
            this.elements.tickDisplay.textContent =
                `Tick: ${progress.current_tick} / ${progress.max_ticks}`;
        }
        if (this.elements.tickProgress) {
            this.elements.tickProgress.style.width = `${tickPercent}%`;
        }

        // Status
        if (this.elements.statusDisplay) {
            this.elements.statusDisplay.textContent = progress.status || 'Unknown';
            this.elements.statusDisplay.className = 'status-badge ' + (progress.status || '');
        }

        // Budget progress
        const budgetPercent = (progress.api_cost_spent / progress.api_cost_limit) * 100;
        if (this.elements.budgetDisplay) {
            this.elements.budgetDisplay.textContent =
                `API Budget: $${progress.api_cost_spent.toFixed(2)} / $${progress.api_cost_limit.toFixed(2)}`;
        }
        if (this.elements.budgetProgress) {
            this.elements.budgetProgress.style.width = `${Math.min(budgetPercent, 100)}%`;
        }

        // Ticks per second
        if (this.elements.tpsDisplay) {
            this.elements.tpsDisplay.textContent =
                `${progress.ticks_per_second.toFixed(2)} ticks/sec`;
        }
    },

    /**
     * Load initial progress from API
     */
    async load() {
        try {
            const progress = await API.getProgress();
            this.update(progress);
        } catch (error) {
            console.error('Failed to load progress:', error);
        }
    }
};

window.ProgressPanel = ProgressPanel;
