/**
 * Artifacts catalog panel
 */

const ArtifactsPanel = {
    elements: {
        tbody: null,
        countBadge: null,
        searchInput: null,
        filterSelect: null
    },

    artifacts: [],

    /**
     * Initialize the artifacts panel
     */
    init() {
        this.elements.tbody = document.getElementById('artifacts-tbody');
        this.elements.countBadge = document.getElementById('artifact-count');
        this.elements.searchInput = document.getElementById('artifact-search');
        this.elements.filterSelect = document.getElementById('artifact-filter');

        // Search handler
        if (this.elements.searchInput) {
            this.elements.searchInput.addEventListener('input', () => {
                this.render();
            });
        }

        // Filter handler
        if (this.elements.filterSelect) {
            this.elements.filterSelect.addEventListener('change', () => {
                this.render();
            });
        }

        // Listen for state updates
        window.wsManager.on('initial_state', (data) => {
            if (data.artifacts) {
                this.updateAll(data.artifacts);
            }
        });

        window.wsManager.on('state_update', () => {
            this.load();
        });
    },

    /**
     * Update all artifacts
     */
    updateAll(artifacts) {
        this.artifacts = artifacts;

        if (this.elements.countBadge) {
            this.elements.countBadge.textContent = artifacts.length;
        }

        this.render();
    },

    /**
     * Render artifacts table based on search/filter
     */
    render() {
        if (!this.elements.tbody) return;

        let filtered = this.artifacts;

        // Apply search filter
        const searchTerm = this.elements.searchInput?.value?.toLowerCase() || '';
        if (searchTerm) {
            filtered = filtered.filter(art =>
                art.artifact_id.toLowerCase().includes(searchTerm) ||
                art.created_by.toLowerCase().includes(searchTerm) ||
                art.artifact_type.toLowerCase().includes(searchTerm)
            );
        }

        // Apply type filter
        const typeFilter = this.elements.filterSelect?.value || '';
        if (typeFilter) {
            filtered = filtered.filter(art =>
                art.artifact_type.toLowerCase().includes(typeFilter.toLowerCase())
            );
        }

        this.elements.tbody.innerHTML = '';

        filtered.forEach(artifact => {
            const row = document.createElement('tr');
            row.style.cursor = 'pointer';

            const execIcon = artifact.executable ? '&#9889;' : '';
            const execTooltip = artifact.executable
                ? 'Executable: Can be invoked by other agents'
                : 'Not executable';

            // Mint status with better tooltips
            let mintDisplay, mintTooltip;
            if (artifact.mint_status === 'scored') {
                mintDisplay = artifact.mint_score?.toFixed(1) || '-';
                mintTooltip = `Mint Score: ${artifact.mint_score?.toFixed(2) || 'N/A'} - Quality rating from external LLM`;
            } else if (artifact.mint_status === 'pending') {
                mintDisplay = '⏳';
                mintTooltip = 'Pending: Submitted to mint, awaiting scoring';
            } else {
                mintDisplay = '-';
                mintTooltip = 'Not submitted: Artifact not yet submitted to mint for scoring';
            }

            // Price display - show base price, indicate if potentially dynamic
            let priceDisplay, priceTooltip;
            const isGenesis = artifact.artifact_id.startsWith('genesis_');

            if (artifact.executable && !isGenesis) {
                // Executable user artifacts may have dynamic pricing via code
                priceDisplay = artifact.price > 0 ? `${artifact.price}*` : '0*';
                priceTooltip = `Base price: ${artifact.price} scrip\n* Executable artifacts may compute dynamic fees`;
            } else if (artifact.price > 0) {
                priceDisplay = artifact.price;
                priceTooltip = `Price: ${artifact.price} scrip to invoke`;
            } else {
                priceDisplay = '0';
                priceTooltip = 'Free: No base cost to invoke';
            }

            row.innerHTML = `
                <td title="Artifact ID: ${this.escapeHtml(artifact.artifact_id)}\nCreated: ${artifact.created_at || 'Unknown'}">${this.truncate(artifact.artifact_id, 15)}</td>
                <td title="Type: ${artifact.artifact_type}">${this.escapeHtml(artifact.artifact_type)}</td>
                <td title="Owner: ${artifact.created_by}">${this.escapeHtml(artifact.created_by)}</td>
                <td title="${priceTooltip}">${priceDisplay}</td>
                <td title="${execTooltip}">${execIcon}</td>
                <td title="${mintTooltip}">${mintDisplay}</td>
            `;

            // Click to show detail
            row.addEventListener('click', () => this.showArtifactDetail(artifact.artifact_id));

            this.elements.tbody.appendChild(row);
        });
    },

    /**
     * Load artifacts from API
     */
    async load() {
        try {
            const artifacts = await API.getArtifacts();
            this.updateAll(artifacts);
        } catch (error) {
            console.error('Failed to load artifacts:', error);
        }
    },

    /**
     * Truncate string with ellipsis
     */
    truncate(str, maxLen) {
        if (str.length <= maxLen) return str;
        return str.substring(0, maxLen - 3) + '...';
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
     * Show artifact detail modal
     */
    async showArtifactDetail(artifactId) {
        try {
            const response = await fetch(`/api/artifacts/${encodeURIComponent(artifactId)}/detail`);
            const detail = await response.json();

            if (detail.error) {
                console.error(detail.error);
                return;
            }

            // Update modal
            const modal = document.getElementById('artifact-modal');
            const title = document.getElementById('artifact-modal-title');
            const info = document.getElementById('artifact-modal-info');
            const content = document.getElementById('artifact-modal-content');
            const ownership = document.getElementById('artifact-modal-ownership');

            if (title) title.textContent = detail.artifact_id;

            if (info) {
                info.innerHTML = `
                    <div class="artifact-info-grid">
                        <div class="info-item">
                            <span class="info-label">Type</span>
                            <span class="info-value">${this.escapeHtml(detail.artifact_type)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Owner</span>
                            <span class="info-value">${this.escapeHtml(detail.created_by)}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Price</span>
                            <span class="info-value">${detail.price} scrip</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Executable</span>
                            <span class="info-value">${detail.executable ? 'Yes' : 'No'}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Mint</span>
                            <span class="info-value">${detail.mint_status} ${detail.mint_score ? `(${detail.mint_score.toFixed(2)})` : ''}</span>
                        </div>
                        <div class="info-item">
                            <span class="info-label">Size</span>
                            <span class="info-value">${detail.size_bytes} bytes</span>
                        </div>
                    </div>
                `;
            }

            if (content) {
                const code = detail.content || '(No content)';
                content.textContent = code;
            }

            if (ownership && detail.ownership_history) {
                if (detail.ownership_history.length > 0) {
                    ownership.innerHTML = detail.ownership_history.map(h =>
                        `<div class="modal-list-item">Tick ${h.tick}: ${h.from_id || '(created)'} → ${h.to_id}</div>`
                    ).join('');
                } else {
                    ownership.innerHTML = '<div class="modal-list-item">Original owner</div>';
                }
            }

            // Show modal
            if (modal) modal.classList.remove('hidden');

            // Close button handler
            const closeBtn = document.getElementById('artifact-modal-close');
            if (closeBtn) {
                closeBtn.onclick = () => modal.classList.add('hidden');
            }

            // Click outside to close
            modal.onclick = (e) => {
                if (e.target === modal) modal.classList.add('hidden');
            };

        } catch (error) {
            console.error('Failed to load artifact detail:', error);
        }
    }
};

window.ArtifactsPanel = ArtifactsPanel;
