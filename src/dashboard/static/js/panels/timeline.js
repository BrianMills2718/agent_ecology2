/**
 * Action timeline panel
 */

const TimelinePanel = {
    elements: {
        content: null,
        agentFilter: null
    },

    actions: [],
    maxItems: 100,

    /**
     * Initialize the timeline panel
     */
    init() {
        this.elements.content = document.getElementById('timeline-content');
        this.elements.agentFilter = document.getElementById('timeline-agent-filter');

        // Filter change handler
        if (this.elements.agentFilter) {
            this.elements.agentFilter.addEventListener('change', () => {
                this.render();
            });
        }

        // Listen for new events
        window.wsManager.on('event', (event) => {
            if (event.event_type === 'action') {
                this.addAction(event);
            }
        });

        window.wsManager.on('initial_state', () => {
            // Load from API for initial state
            this.load();
        });
    },

    /**
     * Add a new action to the timeline
     */
    addAction(event) {
        const data = event.data || event;
        const intent = data.intent || {};

        const action = {
            tick: data.tick || 0,
            timestamp: data.timestamp || event.timestamp,
            agent_id: intent.principal_id || 'unknown',
            action_type: intent.action_type || 'unknown',
            target: intent.artifact_id || null,
            success: !data.error,
            error: data.error || null
        };

        this.actions.unshift(action);

        // Trim to max items
        if (this.actions.length > this.maxItems) {
            this.actions = this.actions.slice(0, this.maxItems);
        }

        this.render();
    },

    /**
     * Update with multiple actions
     */
    updateAll(actions) {
        this.actions = actions.slice(0, this.maxItems);
        this.render();
    },

    /**
     * Render the timeline
     */
    render() {
        if (!this.elements.content) return;

        let filtered = this.actions;

        // Apply agent filter
        const agentFilter = this.elements.agentFilter?.value || '';
        if (agentFilter) {
            filtered = filtered.filter(a => a.agent_id === agentFilter);
        }

        if (filtered.length === 0) {
            this.elements.content.innerHTML = '<div class="timeline-item">No actions yet</div>';
            return;
        }

        this.elements.content.innerHTML = filtered.map(action => {
            const statusClass = action.success ? 'success' : 'failed';
            const targetDisplay = action.target ? ` -> ${this.escapeHtml(action.target)}` : '';

            return `
                <div class="timeline-item">
                    <span class="timeline-tick">T${action.tick}</span>
                    <span class="timeline-agent">${this.escapeHtml(action.agent_id)}</span>
                    <span class="timeline-action ${statusClass}">
                        ${this.escapeHtml(action.action_type)}${targetDisplay}
                    </span>
                </div>
            `;
        }).join('');
    },

    /**
     * Load actions from API
     */
    async load() {
        try {
            const events = await API.getEvents({
                eventTypes: ['action'],
                limit: this.maxItems
            });

            const actions = events.map(event => {
                const data = event.data || {};
                const intent = data.intent || {};
                return {
                    tick: data.tick || 0,
                    timestamp: event.timestamp,
                    agent_id: intent.principal_id || 'unknown',
                    action_type: intent.action_type || 'unknown',
                    target: intent.artifact_id || null,
                    success: !data.error,
                    error: data.error || null
                };
            }).reverse();  // Newest first

            this.updateAll(actions);
        } catch (error) {
            console.error('Failed to load timeline:', error);
        }
    },

    /**
     * Escape HTML for safe display
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

window.TimelinePanel = TimelinePanel;
