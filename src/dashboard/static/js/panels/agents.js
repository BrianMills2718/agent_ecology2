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

            const llmTokensPercent = agent.llm_tokens_quota > 0
                ? (agent.llm_tokens_used / agent.llm_tokens_quota * 100).toFixed(0)
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
                <td>${llmTokensPercent}%</td>
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
            // Fetch agent data and config in parallel
            const [agent, config] = await Promise.all([
                API.getAgent(agentId),
                API.getAgentConfig(agentId)
            ]);

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
                        <div class="modal-stat-label">LLM Tokens</div>
                        <div class="modal-stat-value">${agent.llm_tokens.current.toFixed(0)}/${agent.llm_tokens.quota}</div>
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

            // Update recent thinking
            const thinkingEl = document.getElementById('modal-thinking');
            if (thinkingEl) {
                if (agent.thinking_history && agent.thinking_history.length > 0) {
                    thinkingEl.innerHTML = agent.thinking_history.slice(-10).reverse().map(thought => {
                        const preview = thought.thought_process
                            ? this.escapeHtml(thought.thought_process.substring(0, 150)) + (thought.thought_process.length > 150 ? '...' : '')
                            : '<em>No reasoning content</em>';
                        return `
                            <div class="modal-thinking-item">
                                <div class="thinking-meta">
                                    <span class="timeline-tick">T${thought.tick}</span>
                                    <span class="thinking-tokens-small">${thought.input_tokens}in/${thought.output_tokens}out</span>
                                    <span class="thinking-cost-small">${thought.thinking_cost} tokens</span>
                                </div>
                                <div class="thinking-preview-modal">${preview}</div>
                            </div>
                        `;
                    }).join('');
                } else {
                    thinkingEl.innerHTML = '<div class="modal-list-item">No thinking recorded yet</div>';
                }
            }

            // Update configuration (Plan #108)
            const configEl = document.getElementById('modal-config');
            if (configEl) {
                configEl.innerHTML = this.renderConfig(config);
            }

            // Show modal
            this.elements.modal.classList.remove('hidden');

        } catch (error) {
            console.error('Failed to load agent detail:', error);
        }
    },

    /**
     * Render agent configuration as HTML (Plan #108)
     */
    renderConfig(config) {
        if (!config || !config.config_found) {
            return '<div class="config-not-found">Configuration not found</div>';
        }

        let html = '<div class="config-grid">';

        // Basic model settings
        html += '<div class="config-section">';
        html += '<h4>Model Settings</h4>';
        html += `<div class="config-item"><span class="config-label">LLM Model:</span> <span class="config-value">${this.escapeHtml(config.llm_model || 'default')}</span></div>`;
        html += `<div class="config-item"><span class="config-label">Starting Credits:</span> <span class="config-value">${config.starting_credits}</span></div>`;
        html += `<div class="config-item"><span class="config-label">Enabled:</span> <span class="config-value config-badge ${config.enabled ? 'enabled' : 'disabled'}">${config.enabled ? 'Yes' : 'No'}</span></div>`;
        if (config.temperature !== null && config.temperature !== undefined) {
            html += `<div class="config-item"><span class="config-label">Temperature:</span> <span class="config-value">${config.temperature}</span></div>`;
        }
        if (config.max_tokens !== null && config.max_tokens !== undefined) {
            html += `<div class="config-item"><span class="config-label">Max Tokens:</span> <span class="config-value">${config.max_tokens}</span></div>`;
        }
        html += '</div>';

        // Genotype traits (gen3 agents)
        if (config.genotype && Object.keys(config.genotype).length > 0) {
            html += '<div class="config-section">';
            html += '<h4>Genotype Traits</h4>';
            for (const [trait, value] of Object.entries(config.genotype)) {
                html += `<div class="config-item"><span class="config-label">${this.escapeHtml(trait)}:</span> <span class="config-value config-badge trait">${this.escapeHtml(String(value))}</span></div>`;
            }
            html += '</div>';
        }

        // RAG configuration
        if (config.rag) {
            html += '<div class="config-section">';
            html += '<h4>RAG Settings</h4>';
            if (config.rag.enabled !== undefined) {
                html += `<div class="config-item"><span class="config-label">Enabled:</span> <span class="config-value config-badge ${config.rag.enabled ? 'enabled' : 'disabled'}">${config.rag.enabled ? 'Yes' : 'No'}</span></div>`;
            }
            if (config.rag.top_k !== undefined) {
                html += `<div class="config-item"><span class="config-label">Top K:</span> <span class="config-value">${config.rag.top_k}</span></div>`;
            }
            if (config.rag.similarity_threshold !== undefined) {
                html += `<div class="config-item"><span class="config-label">Similarity Threshold:</span> <span class="config-value">${config.rag.similarity_threshold}</span></div>`;
            }
            html += '</div>';
        }

        // Workflow with state machine (gen3)
        if (config.workflow) {
            html += '<div class="config-section config-section-wide">';
            html += '<h4>Workflow</h4>';

            // State machine
            if (config.workflow.state_machine) {
                const sm = config.workflow.state_machine;
                html += '<div class="config-subsection">';
                html += '<h5>State Machine</h5>';
                if (sm.initial_state) {
                    html += `<div class="config-item"><span class="config-label">Initial State:</span> <span class="config-value config-badge state">${this.escapeHtml(sm.initial_state)}</span></div>`;
                }
                if (sm.states && Object.keys(sm.states).length > 0) {
                    html += '<div class="config-states">';
                    html += '<span class="config-label">States:</span>';
                    html += '<div class="state-list">';
                    for (const [state, stateConfig] of Object.entries(sm.states)) {
                        const transitions = stateConfig.transitions ? Object.keys(stateConfig.transitions).join(', ') : 'none';
                        html += `<div class="state-item"><span class="state-name">${this.escapeHtml(state)}</span> → ${this.escapeHtml(transitions)}</div>`;
                    }
                    html += '</div></div>';
                }
                html += '</div>';
            }

            // Workflow steps
            if (config.workflow.steps && config.workflow.steps.length > 0) {
                html += '<div class="config-subsection">';
                html += '<h5>Steps</h5>';
                html += '<ol class="workflow-steps">';
                for (const step of config.workflow.steps) {
                    const stepName = typeof step === 'string' ? step : (step.name || step.action || JSON.stringify(step));
                    html += `<li>${this.escapeHtml(stepName)}</li>`;
                }
                html += '</ol></div>';
            }
            html += '</div>';
        }

        // Error handling
        if (config.error_handling) {
            html += '<div class="config-section">';
            html += '<h4>Error Handling</h4>';
            if (config.error_handling.max_retries !== undefined) {
                html += `<div class="config-item"><span class="config-label">Max Retries:</span> <span class="config-value">${config.error_handling.max_retries}</span></div>`;
            }
            if (config.error_handling.backoff_factor !== undefined) {
                html += `<div class="config-item"><span class="config-label">Backoff Factor:</span> <span class="config-value">${config.error_handling.backoff_factor}</span></div>`;
            }
            if (config.error_handling.fallback_action) {
                html += `<div class="config-item"><span class="config-label">Fallback:</span> <span class="config-value">${this.escapeHtml(config.error_handling.fallback_action)}</span></div>`;
            }
            html += '</div>';
        }

        html += '</div>';
        return html;
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
