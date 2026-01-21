/**
 * Activity Feed Panel - Shows a unified feed of all activity
 * Updated with entity filters (Plan #144)
 */

const ActivityPanel = {
    container: null,
    typeFilter: null,
    agentFilter: null,
    artifactFilter: null,

    // Activity icons by type
    icons: {
        artifact_created: '📦',
        artifact_updated: '📝',
        escrow_listed: '🏷️',
        escrow_purchased: '🤝',
        escrow_cancelled: '❌',
        scrip_transfer: '💰',
        ownership_transfer: '🔑',
        mint_result: '⭐',
        principal_spawned: '👤',
        thinking: '💭',
        action: '⚡',
    },

    init() {
        this.container = document.getElementById('activity-content');
        this.typeFilter = document.getElementById('activity-type-filter');
        this.agentFilter = document.getElementById('activity-agent-filter');
        this.artifactFilter = document.getElementById('activity-artifact-filter');

        if (!this.container) return;

        // Filter change events
        if (this.typeFilter) {
            this.typeFilter.addEventListener('change', () => this.loadActivity());
        }
        if (this.agentFilter) {
            this.agentFilter.addEventListener('change', () => this.loadActivity());
        }
        if (this.artifactFilter) {
            this.artifactFilter.addEventListener('change', () => this.loadActivity());
        }

        // Populate entity filters (Plan #144)
        this.populateEntityFilters();

        // Listen for state updates to refresh filter options
        if (window.wsManager) {
            window.wsManager.on('state_update', () => this.populateEntityFilters());
        }

        // Initial load
        this.loadActivity();
    },

    /**
     * Populate agent and artifact filter dropdowns (Plan #144)
     */
    async populateEntityFilters() {
        // Populate agent filter
        if (this.agentFilter) {
            try {
                const response = await fetch('/api/agents');
                const data = await response.json();
                const agents = Array.isArray(data) ? data : (data.agents || []);

                const currentValue = this.agentFilter.value;
                this.agentFilter.innerHTML = '<option value="">All Agents</option>';
                agents.forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent.agent_id;
                    option.textContent = agent.agent_id;
                    if (agent.agent_id === currentValue) option.selected = true;
                    this.agentFilter.appendChild(option);
                });
            } catch (err) {
                console.error('Failed to load agents for filter:', err);
            }
        }

        // Populate artifact filter
        if (this.artifactFilter) {
            try {
                const response = await fetch('/api/artifacts?limit=100');
                const data = await response.json();
                const artifacts = Array.isArray(data) ? data : (data.artifacts || []);

                const currentValue = this.artifactFilter.value;
                this.artifactFilter.innerHTML = '<option value="">All Artifacts</option>';
                artifacts.forEach(artifact => {
                    const option = document.createElement('option');
                    option.value = artifact.artifact_id;
                    option.textContent = artifact.artifact_id;
                    if (artifact.artifact_id === currentValue) option.selected = true;
                    this.artifactFilter.appendChild(option);
                });
            } catch (err) {
                console.error('Failed to load artifacts for filter:', err);
            }
        }
    },

    async loadActivity() {
        try {
            let url = '/api/activity?limit=100';

            if (this.typeFilter && this.typeFilter.value) {
                url += `&types=${encodeURIComponent(this.typeFilter.value)}`;
            }

            // Entity filters (Plan #144)
            if (this.agentFilter && this.agentFilter.value) {
                url += `&agent_id=${encodeURIComponent(this.agentFilter.value)}`;
            }
            if (this.artifactFilter && this.artifactFilter.value) {
                url += `&artifact_id=${encodeURIComponent(this.artifactFilter.value)}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            this.renderActivity(data.items);
        } catch (err) {
            console.error('Failed to load activity:', err);
            this.container.innerHTML = '<div class="activity-item">Failed to load activity</div>';
        }
    },

    renderActivity(items) {
        if (!items || items.length === 0) {
            this.container.innerHTML = '<div class="activity-item">No activity yet</div>';
            return;
        }

        this.container.innerHTML = items.map(item => this.renderItem(item)).join('');

        // Add click handlers for links
        this.container.querySelectorAll('.agent-link').forEach(el => {
            el.addEventListener('click', () => {
                const agentId = el.dataset.agentId;
                if (typeof AgentsPanel !== 'undefined' && AgentsPanel.showAgentModal) {
                    AgentsPanel.showAgentModal(agentId);
                }
            });
        });

        this.container.querySelectorAll('.artifact-link').forEach(el => {
            el.addEventListener('click', () => {
                const artifactId = el.dataset.artifactId;
                this.showArtifactModal(artifactId);
            });
        });
    },

    renderItem(item) {
        const icon = this.icons[item.activity_type] || '•';
        const description = this.formatDescription(item);

        return `
            <div class="activity-item">
                <span class="activity-tick">${item.tick}</span>
                <span class="activity-icon">${icon}</span>
                <span class="activity-text">${description}</span>
            </div>
        `;
    },

    formatDescription(item) {
        // Format description with clickable links
        let desc = item.description;

        // Replace agent IDs with links
        if (item.agent_id) {
            desc = desc.replace(
                new RegExp(`\\b${item.agent_id}\\b`, 'g'),
                `<span class="agent-link" data-agent-id="${item.agent_id}">${item.agent_id}</span>`
            );
        }
        if (item.target_id && item.target_id !== item.agent_id) {
            desc = desc.replace(
                new RegExp(`\\b${item.target_id}\\b`, 'g'),
                `<span class="agent-link" data-agent-id="${item.target_id}">${item.target_id}</span>`
            );
        }

        // Replace artifact IDs with links
        if (item.artifact_id) {
            desc = desc.replace(
                new RegExp(`\\b${item.artifact_id}\\b`, 'g'),
                `<span class="artifact-link" data-artifact-id="${item.artifact_id}">${item.artifact_id}</span>`
            );
        }

        // Highlight amounts
        if (item.amount) {
            desc = desc.replace(
                new RegExp(`\\b${item.amount}\\b`),
                `<span class="amount">${item.amount}</span>`
            );
        }

        return desc;
    },

    async showArtifactModal(artifactId) {
        try {
            const response = await fetch(`/api/artifacts/${encodeURIComponent(artifactId)}/detail`);
            const artifact = await response.json();

            if (artifact.error) {
                console.error('Artifact not found:', artifactId);
                return;
            }

            // Populate modal
            const modal = document.getElementById('artifact-modal');
            const title = document.getElementById('artifact-modal-title');
            const info = document.getElementById('artifact-modal-info');
            const content = document.getElementById('artifact-modal-content');
            const ownership = document.getElementById('artifact-modal-ownership');

            title.textContent = artifact.artifact_id;

            // Info section
            info.innerHTML = `
                <div class="artifact-info-grid">
                    <div class="info-item">
                        <span class="info-label">Type</span>
                        <span class="info-value">${artifact.artifact_type}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Owner</span>
                        <span class="info-value">${artifact.created_by}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Executable</span>
                        <span class="info-value">${artifact.executable ? 'Yes' : 'No'}</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Size</span>
                        <span class="info-value">${artifact.size_bytes} bytes</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Price</span>
                        <span class="info-value">${artifact.price} scrip</span>
                    </div>
                    <div class="info-item">
                        <span class="info-label">Invocations</span>
                        <span class="info-value">${artifact.invocation_count}</span>
                    </div>
                    ${artifact.mint_score !== null ? `
                    <div class="info-item">
                        <span class="info-label">Mint Score</span>
                        <span class="info-value">${artifact.mint_score.toFixed(1)}</span>
                    </div>
                    ` : ''}
                </div>
            `;

            // Content section
            if (artifact.content) {
                content.textContent = artifact.content;
                content.parentElement.style.display = 'block';
            } else {
                content.textContent = '(No content available)';
                content.parentElement.style.display = 'block';
            }

            // Ownership history
            if (artifact.ownership_history && artifact.ownership_history.length > 0) {
                ownership.innerHTML = artifact.ownership_history.map(transfer => `
                    <div class="modal-list-item">
                        ${transfer.from_id} → ${transfer.to_id}
                        <span style="color: var(--text-secondary); font-size: 0.7rem;">
                            ${new Date(transfer.timestamp).toLocaleTimeString()}
                        </span>
                    </div>
                `).join('');
            } else {
                ownership.innerHTML = '<div class="modal-list-item">No ownership transfers</div>';
            }

            // Activity timeline (Plan #144)
            const activityEl = document.getElementById('artifact-modal-activity');
            if (activityEl) {
                try {
                    const activityResp = await fetch(`/api/activity?artifact_id=${encodeURIComponent(artifactId)}&limit=50`);
                    const activityData = await activityResp.json();
                    if (activityData.items && activityData.items.length > 0) {
                        activityEl.innerHTML = activityData.items.map(item => {
                            const icon = this.icons[item.activity_type] || '•';
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
            modal.classList.remove('hidden');

            // Close handler
            const closeBtn = document.getElementById('artifact-modal-close');
            closeBtn.onclick = () => modal.classList.add('hidden');
            modal.onclick = (e) => {
                if (e.target === modal) modal.classList.add('hidden');
            };

        } catch (err) {
            console.error('Failed to load artifact detail:', err);
        }
    },

    // Called when new events arrive via WebSocket
    refresh() {
        this.loadActivity();
    },
};

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    ActivityPanel.init();
});
