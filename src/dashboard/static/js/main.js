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
            EventsPanel.init();
            ChartsPanel.init();
            GenesisPanel.init();
            ControlsPanel.init();

            // Initialize new panels (check if they exist)
            if (typeof NetworkPanel !== 'undefined') {
                NetworkPanel.init();
            }
            if (typeof ActivityPanel !== 'undefined') {
                ActivityPanel.init();
            }
            if (typeof ThinkingPanel !== 'undefined') {
                this.thinkingPanel = new ThinkingPanel();
                this.thinkingPanel.init();
            }

            // Set up charts panel toggle
            this.setupChartsToggle();

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

            // Load events
            await EventsPanel.load();

            // Set up WebSocket handlers for live updates
            this.setupWebSocketHandlers();

        } catch (error) {
            console.error('Failed to load initial data:', error);
            // Don't throw - WebSocket will update when simulation runs
        }
    },

    /**
     * Set up WebSocket event handlers for live updates
     */
    setupWebSocketHandlers() {
        // On new events, refresh relevant panels
        window.wsManager.on('event', (event) => {
            // Refresh network and activity panels on relevant events
            if (typeof NetworkPanel !== 'undefined' && NetworkPanel.refresh) {
                NetworkPanel.refresh();
            }
            if (typeof ActivityPanel !== 'undefined' && ActivityPanel.refresh) {
                ActivityPanel.refresh();
            }
            // Refresh thinking panel on thinking events
            if (this.thinkingPanel && event.event_type === 'thinking') {
                this.thinkingPanel.refresh();
            }
        });

        // On state updates
        window.wsManager.on('state_update', (data) => {
            if (data.progress) {
                ProgressPanel.update(data.progress);
            }
        });
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

        // Refresh new panels
        if (typeof NetworkPanel !== 'undefined' && NetworkPanel.refresh) {
            NetworkPanel.refresh();
        }
        if (typeof ActivityPanel !== 'undefined' && ActivityPanel.refresh) {
            ActivityPanel.refresh();
        }
        if (this.thinkingPanel) {
            this.thinkingPanel.refresh();
        }
    },

    /**
     * Set up collapsible charts panel
     */
    setupChartsToggle() {
        const toggle = document.getElementById('charts-toggle');
        if (toggle) {
            toggle.addEventListener('click', () => {
                const panel = toggle.closest('.panel');
                if (panel) {
                    panel.classList.toggle('collapsed');
                    const icon = panel.querySelector('.collapse-icon');
                    if (icon) {
                        icon.textContent = panel.classList.contains('collapsed') ? '+' : 'x';
                    }
                }
            });
        }
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

    // Escape to close modals
    if (e.key === 'Escape') {
        AgentsPanel.closeModal();
        // Also close artifact modal
        const artifactModal = document.getElementById('artifact-modal');
        if (artifactModal) {
            artifactModal.classList.add('hidden');
        }
    }
});

// Export for use
window.Dashboard = Dashboard;
