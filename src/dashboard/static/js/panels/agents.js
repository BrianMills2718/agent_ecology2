/**
 * Agents status panel
 */

const AgentsPanel = {
    elements: {
        tbody: null,
        countBadge: null,
        modal: null,
        modalClose: null
    },

    agents: [],

    /**
     * Initialize the agents panel
     */
    init() {
        this.elements.tbody = document.getElementById('agents-tbody');
        this.elements.countBadge = document.getElementById('agent-count');
        this.elements.modal = document.getElementById('agent-modal');
        this.elements.modalClose = document.getElementById('modal-close');

        // Modal close handler
        if (this.elements.modalClose) {
            this.elements.modalClose.addEventListener('click', () => {
                this.closeModal();
            });
        }

        // Click outside modal to close
        if (this.elements.modal) {
            this.elements.modal.addEventListener('click', (e) => {
                if (e.target === this.elements.modal) {
                    this.closeModal();
                }
            });
        }

        // Listen for state updates
        window.wsManager.on('initial_state', (data) => {
            if (data.agents) {
                this.updateAll(data.agents);
            }
        });

        window.wsManager.on('state_update', () => {
            // Refresh agents on state update
            this.load();
        });
    },

    /**
     * Update all agents
     */
    updateAll(agents) {
        this.agents = agents;

        if (this.elements.countBadge) {
            this.elements.countBadge.textContent = agents.length;
        }

        if (!this.elements.tbody) return;

        this.elements.tbody.innerHTML = '';

        agents.forEach(agent => {
            const row = document.createElement('tr');
            row.addEventListener('click', () => this.showAgentDetail(agent.agent_id));

            const computePercent = agent.compute_quota > 0
                ? (agent.compute_used / agent.compute_quota * 100).toFixed(0)
                : 0;
            const diskPercent = agent.disk_quota > 0
                ? (agent.disk_used / agent.disk_quota * 100).toFixed(0)
                : 0;

            const statusClass = agent.status === 'active' ? 'status-active'
                : agent.status === 'low_resources' ? 'status-low-resources'
                : 'status-frozen';

            row.innerHTML = `
                <td>${this.escapeHtml(agent.agent_id)}</td>
                <td>${agent.scrip}</td>
                <td>${computePercent}%</td>
                <td>${diskPercent}%</td>
                <td class="${statusClass}">${agent.status}</td>
                <td>${agent.action_count}</td>
            `;

            this.elements.tbody.appendChild(row);
        });

        // Update timeline agent filter
        this.updateTimelineFilter(agents);
    },

    /**
     * Update timeline agent filter dropdown
     */
    updateTimelineFilter(agents) {
        const filter = document.getElementById('timeline-agent-filter');
        if (!filter) return;

        // Keep current selection
        const currentValue = filter.value;

        // Clear except "All Agents"
        filter.innerHTML = '<option value="">All Agents</option>';

        agents.forEach(agent => {
            const option = document.createElement('option');
            option.value = agent.agent_id;
            option.textContent = agent.agent_id;
            filter.appendChild(option);
        });

        // Restore selection if still valid
        if (currentValue) {
            filter.value = currentValue;
        }
    },

    /**
     * Show agent detail modal
     */
    async showAgentDetail(agentId) {
        try {
            const agent = await API.getAgent(agentId);
            if (agent.error) {
                console.error(agent.error);
                return;
            }

            // Update modal title
            document.getElementById('modal-agent-id').textContent = agentId;

            // Update balances
            const balancesEl = document.getElementById('modal-balances');
            if (balancesEl) {
                balancesEl.innerHTML = `
                    <div class="modal-stat">
                        <div class="modal-stat-label">Scrip</div>
                        <div class="modal-stat-value">${agent.scrip}</div>
                    </div>
                    <div class="modal-stat">
                        <div class="modal-stat-label">Compute</div>
                        <div class="modal-stat-value">${agent.compute.current.toFixed(0)}/${agent.compute.quota}</div>
                    </div>
                    <div class="modal-stat">
                        <div class="modal-stat-label">Disk</div>
                        <div class="modal-stat-value">${agent.disk.used.toFixed(0)}/${agent.disk.quota}</div>
                    </div>
                `;
            }

            // Update artifacts owned
            const artifactsEl = document.getElementById('modal-artifacts');
            if (artifactsEl) {
                if (agent.artifacts_owned && agent.artifacts_owned.length > 0) {
                    artifactsEl.innerHTML = agent.artifacts_owned.map(id =>
                        `<div class="modal-list-item">${this.escapeHtml(id)}</div>`
                    ).join('');
                } else {
                    artifactsEl.innerHTML = '<div class="modal-list-item">No artifacts owned</div>';
                }
            }

            // Update recent actions
            const actionsEl = document.getElementById('modal-actions');
            if (actionsEl) {
                if (agent.actions && agent.actions.length > 0) {
                    actionsEl.innerHTML = agent.actions.slice(-20).reverse().map(action => {
                        const statusClass = action.success ? 'success' : 'failed';
                        return `
                            <div class="modal-list-item">
                                <span class="timeline-tick">T${action.tick}</span>
                                <span class="timeline-action ${statusClass}">
                                    ${action.action_type}${action.target ? ` -> ${action.target}` : ''}
                                </span>
                            </div>
                        `;
                    }).join('');
                } else {
                    actionsEl.innerHTML = '<div class="modal-list-item">No actions yet</div>';
                }
            }

            // Show modal
            this.elements.modal.classList.remove('hidden');

        } catch (error) {
            console.error('Failed to load agent detail:', error);
        }
    },

    /**
     * Close the modal
     */
    closeModal() {
        if (this.elements.modal) {
            this.elements.modal.classList.add('hidden');
        }
    },

    /**
     * Load agents from API
     */
    async load() {
        try {
            const agents = await API.getAgents();
            this.updateAll(agents);
        } catch (error) {
            console.error('Failed to load agents:', error);
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

window.AgentsPanel = AgentsPanel;
