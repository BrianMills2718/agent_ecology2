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
                art.owner_id.toLowerCase().includes(searchTerm) ||
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

            const execIcon = artifact.executable ? '&#9889;' : '';  // Lightning bolt
            const oracleDisplay = artifact.oracle_status === 'scored'
                ? artifact.oracle_score?.toFixed(1) || '-'
                : artifact.oracle_status === 'pending'
                ? '...'
                : '-';

            row.innerHTML = `
                <td title="${this.escapeHtml(artifact.artifact_id)}">${this.truncate(artifact.artifact_id, 15)}</td>
                <td>${this.escapeHtml(artifact.artifact_type)}</td>
                <td>${this.escapeHtml(artifact.owner_id)}</td>
                <td>${artifact.price}</td>
                <td>${execIcon}</td>
                <td>${oracleDisplay}</td>
            `;

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
    }
};

window.ArtifactsPanel = ArtifactsPanel;
