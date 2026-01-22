/**
 * Agents status panel with pagination (Plan #142)
 */

const AgentsPanel = {
    elements: {
        tbody: null,
        countBadge: null,
        modal: null,
        modalClose: null,
        pagination: null
    },

    agents: [],
    
    // Pagination state (Plan #142)
    currentPage: 1,
    rowsPerPage: 25,
    totalAgents: 0,

    /**
     * Initialize the agents panel
     */
    init() {
        this.elements.tbody = document.getElementById('agents-tbody');
        this.elements.countBadge = document.getElementById('agent-count');
        this.elements.modal = document.getElementById('agent-modal');
        this.elements.modalClose = document.getElementById('modal-close');
        this.elements.pagination = document.getElementById('agents-pagination');

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

        // Plan #145: Export button handler
        const exportBtn = document.getElementById('agents-export');
        if (exportBtn) {
            exportBtn.addEventListener('click', () => this.exportToCSV());
        }

        // Listen for state updates
        window.wsManager.on('initial_state', (data) => {
            if (data.agents) {
                this.updateAll(data.agents, data.total || data.agents.length);
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
    updateAll(agents, total = null) {
        this.agents = agents;
        this.totalAgents = total !== null ? total : agents.length;

        if (this.elements.countBadge) {
            this.elements.countBadge.textContent = this.totalAgents;
        }

        if (!this.elements.tbody) return;

        this.elements.tbody.innerHTML = '';

        agents.forEach(agent => {
            const row = document.createElement('tr');
            row.addEventListener('click', () => this.showAgentDetail(agent.agent_id));

            // Plan #153: Budget-based display
            const budgetRemaining = agent.llm_budget_remaining || 0;
            const budgetInitial = agent.llm_budget_initial || 0;
            const budgetDisplay = budgetInitial > 0
                ? `$${budgetRemaining.toFixed(2)}/$${budgetInitial.toFixed(2)}`
                : (agent.llm_tokens_quota > 0
                    ? `${((agent.llm_tokens_used / agent.llm_tokens_quota) * 100).toFixed(0)}%`
                    : '0%');

            const diskPercent = agent.disk_quota > 0
                ? (agent.disk_used / agent.disk_quota * 100).toFixed(0)
                : 0;

            const statusClass = agent.status === 'active' ? 'status-active'
                : agent.status === 'low_resources' ? 'status-low-resources'
                : 'status-frozen';

            // Plan #145: Add frozen diagnostic reason
            let frozenReason = '';
            if (agent.status === 'frozen') {
                if (budgetInitial > 0 && budgetRemaining <= 0) {
                    frozenReason = 'LLM budget exhausted';
                } else if (agent.llm_tokens_quota > 0 && agent.llm_tokens_used >= agent.llm_tokens_quota) {
                    frozenReason = 'LLM tokens exhausted';
                } else if (agent.scrip <= 0) {
                    frozenReason = 'Out of scrip';
                } else if (diskPercent >= 100) {
                    frozenReason = 'Disk quota exceeded';
                } else {
                    frozenReason = 'Resources depleted';
                }
            }
            const statusAttr = frozenReason ? ` data-reason="${frozenReason}"` : '';

            row.innerHTML = `
                <td>${this.escapeHtml(agent.agent_id)}</td>
                <td>${agent.scrip}</td>
                <td>${budgetDisplay}</td>
                <td>${diskPercent}%</td>
                <td class="${statusClass}"${statusAttr}>${agent.status}</td>
                <td>${agent.action_count}</td>
            `;

            this.elements.tbody.appendChild(row);
        });

        // Update timeline agent filter
        this.updateTimelineFilter(agents);
        
        // Render pagination controls (Plan #142)
        this.renderPagination();
    },

    /**
     * Render pagination controls (Plan #142)
     */
    renderPagination() {
        if (!this.elements.pagination) return;

        const totalPages = Math.ceil(this.totalAgents / this.rowsPerPage);
        
        if (totalPages <= 1) {
            this.elements.pagination.innerHTML = '';
            return;
        }

        this.elements.pagination.innerHTML = `
            <button class="page-btn" data-action="prev" ${this.currentPage <= 1 ? 'disabled' : ''}>&lt;</button>
            <span class="page-info">Page ${this.currentPage} of ${totalPages}</span>
            <button class="page-btn" data-action="next" ${this.currentPage >= totalPages ? 'disabled' : ''}>&gt;</button>
            <select class="rows-per-page">
                <option value="25" ${this.rowsPerPage === 25 ? 'selected' : ''}>25</option>
                <option value="50" ${this.rowsPerPage === 50 ? 'selected' : ''}>50</option>
                <option value="100" ${this.rowsPerPage === 100 ? 'selected' : ''}>100</option>
            </select>
        `;

        // Add event listeners
        this.elements.pagination.querySelector('[data-action="prev"]')?.addEventListener('click', () => {
            if (this.currentPage > 1) {
                this.currentPage--;
                this.load();
            }
        });

        this.elements.pagination.querySelector('[data-action="next"]')?.addEventListener('click', () => {
            if (this.currentPage < totalPages) {
                this.currentPage++;
                this.load();
            }
        });

        this.elements.pagination.querySelector('.rows-per-page')?.addEventListener('change', (e) => {
            this.rowsPerPage = parseInt(e.target.value);
            this.currentPage = 1; // Reset to first page
            this.load();
        });
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

            // Update balances (Plan #153: show budget prominently)
            const balancesEl = document.getElementById('modal-balances');
            if (balancesEl) {
                // Plan #153: Show budget if available, fallback to tokens
                const budgetHtml = agent.llm_budget && agent.llm_budget.initial > 0
                    ? `<div class="modal-stat">
                        <div class="modal-stat-label">LLM Budget</div>
                        <div class="modal-stat-value">$${agent.llm_budget.remaining.toFixed(4)} / $${agent.llm_budget.initial.toFixed(2)}</div>
                       </div>`
                    : `<div class="modal-stat">
                        <div class="modal-stat-label">LLM Tokens</div>
                        <div class="modal-stat-value">${agent.llm_tokens.current.toFixed(0)}/${agent.llm_tokens.quota}</div>
                       </div>`;

                balancesEl.innerHTML = `
                    <div class="modal-stat">
                        <div class="modal-stat-label">Scrip</div>
                        <div class="modal-stat-value">${agent.scrip}</div>
                    </div>
                    ${budgetHtml}
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
                        const preview = thought.reasoning
                            ? this.escapeHtml(thought.reasoning.substring(0, 150)) + (thought.reasoning.length > 150 ? '...' : '')
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

            // Update activity timeline (Plan #144)
            const activityEl = document.getElementById('modal-activity');
            if (activityEl) {
                try {
                    const activityResp = await fetch(`/api/activity?agent_id=${encodeURIComponent(agentId)}&limit=50`);
                    const activityData = await activityResp.json();
                    if (activityData.items && activityData.items.length > 0) {
                        const icons = {
                            artifact_created: '📦',
                            artifact_updated: '📝',
                            escrow_listed: '🏷️',
                            escrow_purchased: '🤝',
                            escrow_cancelled: '❌',
                            scrip_transfer: '💰',
                            ownership_transfer: '🔑',
                            mint_result: '⭐',
                            thinking: '💭',
                            action: '⚡',
                        };
                        activityEl.innerHTML = activityData.items.map(item => {
                            const icon = icons[item.activity_type] || '•';
                            return `
                                <div class="modal-list-item">
                                    <span class="activity-tick">${item.tick}</span>
                                    <span class="activity-icon">${icon}</span>
                                    <span class="activity-text">${item.description}</span>
                                </div>
                            `;
                        }).join('');
                    } else {
                        activityEl.innerHTML = '<div class="modal-list-item">No activity recorded</div>';
                    }
                } catch (err) {
                    activityEl.innerHTML = '<div class="modal-list-item">Failed to load activity</div>';
                }
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
     * Load agents from API with pagination (Plan #142)
     */
    async load() {
        try {
            const offset = (this.currentPage - 1) * this.rowsPerPage;
            const response = await API.getAgents(this.rowsPerPage, offset);
            
            // Handle both old (array) and new (object with pagination) response formats
            if (Array.isArray(response)) {
                this.updateAll(response);
            } else {
                this.updateAll(response.agents, response.total);
            }
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
    },

    /**
     * Export agents to CSV (Plan #145, #153)
     */
    exportToCSV() {
        if (this.agents.length === 0) {
            alert('No agents to export');
            return;
        }

        // CSV header (Plan #153: added budget columns)
        const headers = ['ID', 'Scrip', 'Budget Initial', 'Budget Spent', 'Budget Remaining', 'LLM Tokens Used', 'LLM Tokens Quota', 'Disk Used', 'Disk Quota', 'Status', 'Actions'];
        const rows = [headers.join(',')];

        // CSV rows
        this.agents.forEach(agent => {
            const row = [
                `"${agent.agent_id}"`,
                agent.scrip,
                agent.llm_budget_initial || 0,
                agent.llm_budget_spent || 0,
                agent.llm_budget_remaining || 0,
                agent.llm_tokens_used,
                agent.llm_tokens_quota,
                agent.disk_used,
                agent.disk_quota,
                agent.status,
                agent.action_count
            ];
            rows.push(row.join(','));
        });

        // Create download
        const csv = rows.join('\n');
        const blob = new Blob([csv], { type: 'text/csv' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `agents_export_${new Date().toISOString().slice(0, 10)}.csv`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    }
};

window.AgentsPanel = AgentsPanel;
