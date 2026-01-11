/**
 * Main application entry point for the Agent Ecology Dashboard
 */

const Dashboard = {
    /**
     * Initialize the dashboard
     */
    async init() {
        console.log('Initializing Agent Ecology Dashboard...');

        try {
            // Initialize all panels
            ProgressPanel.init();
            AgentsPanel.init();
            ArtifactsPanel.init();
            TimelinePanel.init();
            EventsPanel.init();
            ChartsPanel.init();
            GenesisPanel.init();
            ControlsPanel.init();

            // Connect WebSocket
            window.wsManager.connect();

            // Load initial data from API
            await this.loadInitialData();

            console.log('Dashboard initialized successfully');

        } catch (error) {
            console.error('Failed to initialize dashboard:', error);
            this.showError('Failed to initialize dashboard. Check console for details.');
        }
    },

    /**
     * Load initial data from API
     */
    async loadInitialData() {
        try {
            // Load state
            const state = await API.getState();

            // Update all panels with initial data
            if (state.progress) {
                ProgressPanel.update(state.progress);
            }
            if (state.agents) {
                AgentsPanel.updateAll(state.agents);
            }
            if (state.artifacts) {
                ArtifactsPanel.updateAll(state.artifacts);
            }
            if (state.genesis) {
                GenesisPanel.update(state.genesis);
            }

            // Load chart data
            await ChartsPanel.loadAll();

            // Load timeline
            await TimelinePanel.load();

            // Load events
            await EventsPanel.load();

        } catch (error) {
            console.error('Failed to load initial data:', error);
            // Don't throw - WebSocket will update when simulation runs
        }
    },

    /**
     * Show error message to user
     */
    showError(message) {
        // Simple alert for now - could be replaced with toast/notification
        console.error(message);
    },

    /**
     * Refresh all data
     */
    async refresh() {
        await this.loadInitialData();
    }
};

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    Dashboard.init();
});

// Handle visibility change - refresh when tab becomes visible
document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') {
        Dashboard.refresh();
    }
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl+R or Cmd+R to refresh (prevent default browser refresh)
    if ((e.ctrlKey || e.metaKey) && e.key === 'r') {
        e.preventDefault();
        Dashboard.refresh();
    }

    // Escape to close modal
    if (e.key === 'Escape') {
        AgentsPanel.closeModal();
    }
});

// Export for use
window.Dashboard = Dashboard;
