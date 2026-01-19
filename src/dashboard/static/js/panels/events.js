/**
 * Live event stream panel
 */

const EventsPanel = {
    elements: {
        content: null,
        pauseBtn: null,
        clearBtn: null,
        typeFilter: null
    },

    events: [],
    maxEvents: 200,
    paused: false,

    /**
     * Initialize the events panel
     */
    init() {
        this.elements.content = document.getElementById('events-content');
        this.elements.pauseBtn = document.getElementById('events-pause');
        this.elements.clearBtn = document.getElementById('events-clear');
        this.elements.typeFilter = document.getElementById('event-type-filter');

        // Pause button handler
        if (this.elements.pauseBtn) {
            this.elements.pauseBtn.addEventListener('click', () => {
                this.togglePause();
            });
        }

        // Clear button handler
        if (this.elements.clearBtn) {
            this.elements.clearBtn.addEventListener('click', () => {
                this.clear();
            });
        }

        // Filter change handler
        if (this.elements.typeFilter) {
            this.elements.typeFilter.addEventListener('change', () => {
                this.render();
            });
        }

        // Listen for new events
        window.wsManager.on('event', (event) => {
            this.addEvent(event);
        });

        window.wsManager.on('initial_state', () => {
            this.load();
        });
    },

    /**
     * Add a new event
     */
    addEvent(event) {
        if (this.paused) return;

        this.events.unshift(event);

        // Trim to max events
        if (this.events.length > this.maxEvents) {
            this.events = this.events.slice(0, this.maxEvents);
        }

        this.render();
    },

    /**
     * Render the event stream
     */
    render() {
        if (!this.elements.content) return;

        let filtered = this.events;

        // Apply type filter
        const selectedTypes = Array.from(this.elements.typeFilter?.selectedOptions || [])
            .map(opt => opt.value);

        if (selectedTypes.length > 0) {
            filtered = filtered.filter(e => selectedTypes.includes(e.event_type));
        }

        if (filtered.length === 0) {
            this.elements.content.innerHTML = '<div class="event-item">No events yet</div>';
            return;
        }

        this.elements.content.innerHTML = filtered.slice(0, 50).map(event => {
            const time = this.formatTime(event.timestamp);
            const typeClass = this.getEventClass(event.event_type);
            const summary = this.summarizeEvent(event);

            return `
                <div class="event-item ${typeClass}">
                    <span class="event-type">${event.event_type}</span>
                    <span class="event-time">${time}</span>
                    <span class="event-data">${this.escapeHtml(summary)}</span>
                </div>
            `;
        }).join('');
    },

    /**
     * Get CSS class for event type
     */
    getEventClass(eventType) {
        switch (eventType) {
            case 'action': return 'event-action';
            case 'thinking': return 'event-thinking';
            case 'mint': return 'event-mint';
            case 'intent_rejected':
            case 'thinking_failed': return 'event-error';
            default: return '';
        }
    },

    /**
     * Summarize event data for display
     */
    summarizeEvent(event) {
        const data = event.data || {};

        switch (event.event_type) {
            case 'tick':
                return `Tick ${data.tick}`;

            case 'thinking':
                return `${data.principal_id}: ${data.input_tokens}in/${data.output_tokens}out tokens`;

            case 'thinking_failed':
                return `${data.principal_id}: ${data.reason}`;

            case 'action':
                // Handle both formats: wrapped in intent object or flat
                const intent = data.intent || {};
                const principalId = intent.principal_id || data.agent_id || data.principal_id || 'unknown';
                const actionType = intent.action_type || data.action_type || 'action';
                const artifactId = intent.artifact_id || data.artifact_id;
                return `${principalId}: ${actionType}${artifactId ? ' -> ' + artifactId : ''}`;

            case 'intent_rejected':
                return `${data.principal_id}: ${data.error}`;

            case 'mint':
                // Handle both old format (artifact_id, score, scrip_minted) and new (principal_id, amount)
                if (data.artifact_id) {
                    return `${data.artifact_id}: score=${data.score || 0}, minted=${data.scrip_minted || 0}`;
                }
                return `${data.principal_id || 'unknown'}: minted ${data.amount || 0} scrip`;

            case 'world_init':
                return `Initialized with ${(data.principals || []).length} agents`;

            case 'max_ticks':
                return 'Simulation completed';

            case 'budget_pause':
                return 'Budget exhausted';

            default:
                return JSON.stringify(data).slice(0, 50);
        }
    },

    /**
     * Format timestamp for display
     */
    formatTime(timestamp) {
        if (!timestamp) return '';
        try {
            const date = new Date(timestamp);
            return date.toLocaleTimeString();
        } catch {
            return '';
        }
    },

    /**
     * Toggle pause state
     */
    togglePause() {
        this.paused = !this.paused;
        if (this.elements.pauseBtn) {
            this.elements.pauseBtn.textContent = this.paused ? '>' : '||';
            this.elements.pauseBtn.title = this.paused ? 'Resume' : 'Pause';
        }
    },

    /**
     * Clear all events
     */
    clear() {
        this.events = [];
        this.render();
    },

    /**
     * Load events from API
     */
    async load() {
        try {
            const events = await API.getEvents({ limit: this.maxEvents });
            this.events = events.reverse();  // Newest first
            this.render();
        } catch (error) {
            console.error('Failed to load events:', error);
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

window.EventsPanel = EventsPanel;
