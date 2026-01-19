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

        // Elapsed time and event count (replaced tick counter)
        const elapsed = progress.elapsed_seconds || 0;
        const events = progress.current_tick || 0;  // current_tick is now event counter
        if (this.elements.tickDisplay) {
            this.elements.tickDisplay.textContent =
                `${this.formatDuration(elapsed)} | ${events} events`;
        }
        // Progress bar shows nothing useful without max_ticks - hide or repurpose
        if (this.elements.tickProgress) {
            // Could show time-based progress if we had a max_duration, for now just hide
            this.elements.tickProgress.style.width = '0%';
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
                `API Budget: $${progress.api_cost_spent.toFixed(4)} / $${progress.api_cost_limit.toFixed(2)}`;
        }
        if (this.elements.budgetProgress) {
            this.elements.budgetProgress.style.width = `${Math.min(budgetPercent, 100)}%`;
        }

        // Events per second (renamed from ticks per second)
        if (this.elements.tpsDisplay) {
            const eps = progress.events_per_second || 0;
            this.elements.tpsDisplay.textContent = `${eps.toFixed(2)} events/sec`;
        }
    },

    /**
     * Format duration in seconds to human-readable string
     */
    formatDuration(seconds) {
        if (seconds < 60) {
            return `${seconds.toFixed(0)}s`;
        } else if (seconds < 3600) {
            const mins = Math.floor(seconds / 60);
            const secs = Math.floor(seconds % 60);
            return `${mins}m ${secs}s`;
        } else {
            const hours = Math.floor(seconds / 3600);
            const mins = Math.floor((seconds % 3600) / 60);
            return `${hours}h ${mins}m`;
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
