/**
 * Activity Feed Panel - Shows a unified feed of all activity
 */

const ActivityPanel = {
    container: null,
    typeFilter: null,

    // Activity icons by type
    icons: {
        artifact_created: '📦',
        artifact_updated: '📝',
        escrow_listed: '🏷️',
        escrow_purchased: '🤝',
        escrow_cancelled: '❌',
        scrip_transfer: '💰',
        ownership_transfer: '🔑',
        oracle_mint: '⭐',
        principal_spawned: '👤',
        thinking: '💭',
        action: '⚡',
    },

    init() {
        this.container = document.getElementById('activity-content');
        this.typeFilter = document.getElementById('activity-type-filter');

        if (!this.container) return;

        // Filter change event
        if (this.typeFilter) {
            this.typeFilter.addEventListener('change', () => {
                this.loadActivity();
            });
        }

        // Initial load
        this.loadActivity();
    },

    async loadActivity() {
        try {
            let url = '/api/activity?limit=100';

            if (this.typeFilter && this.typeFilter.value) {
                url += `&types=${encodeURIComponent(this.typeFilter.value)}`;
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
                        <span class="info-value">${artifact.owner_id}</span>
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
                    ${artifact.oracle_score !== null ? `
                    <div class="info-item">
                        <span class="info-label">Oracle Score</span>
                        <span class="info-value">${artifact.oracle_score.toFixed(1)}</span>
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
