/**
 * Global search component (Plan #147)
 * Provides typeahead search across agents, artifacts, and events
 */

class GlobalSearch {
    constructor() {
        this.searchInput = document.getElementById('global-search');
        this.searchResults = document.getElementById('search-results');
        this.debounceTimer = null;
        this.debounceDelay = 250;
        this.minQueryLength = 2;
        this.isOpen = false;

        this.init();
    }

    init() {
        if (!this.searchInput || !this.searchResults) {
            return;
        }

        // Input event for typeahead
        this.searchInput.addEventListener('input', (e) => {
            this.handleInput(e.target.value);
        });

        // Focus/blur events
        this.searchInput.addEventListener('focus', () => {
            if (this.searchInput.value.length >= this.minQueryLength) {
                this.showResults();
            }
        });

        // Close on outside click
        document.addEventListener('click', (e) => {
            if (!this.searchInput.contains(e.target) && !this.searchResults.contains(e.target)) {
                this.hideResults();
            }
        });

        // Keyboard navigation
        this.searchInput.addEventListener('keydown', (e) => {
            this.handleKeydown(e);
        });

        // Escape to close
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && this.isOpen) {
                this.hideResults();
                this.searchInput.blur();
            }
        });
    }

    handleInput(query) {
        // Clear previous timer
        if (this.debounceTimer) {
            clearTimeout(this.debounceTimer);
        }

        if (query.length < this.minQueryLength) {
            this.hideResults();
            return;
        }

        // Debounce search
        this.debounceTimer = setTimeout(() => {
            this.performSearch(query);
        }, this.debounceDelay);
    }

    async performSearch(query) {
        try {
            const response = await fetch(`/api/search?q=${encodeURIComponent(query)}&limit=10`);
            if (!response.ok) {
                throw new Error('Search failed');
            }
            const data = await response.json();
            this.renderResults(data);
        } catch (error) {
            console.error('Search error:', error);
            this.renderError();
        }
    }

    renderResults(data) {
        const { results, counts } = data;
        const totalCount = counts.agents + counts.artifacts + counts.events;

        if (totalCount === 0) {
            this.searchResults.innerHTML = `
                <div class="search-empty">
                    No results found for "${data.query}"
                </div>
            `;
            this.showResults();
            return;
        }

        let html = '';

        // Agents section
        if (results.agents.length > 0) {
            html += this.renderSection('Agents', results.agents, 'agent');
        }

        // Artifacts section
        if (results.artifacts.length > 0) {
            html += this.renderSection('Artifacts', results.artifacts, 'artifact');
        }

        // Events section
        if (results.events.length > 0) {
            html += this.renderSection('Events', results.events, 'event');
        }

        this.searchResults.innerHTML = html;
        this.attachResultHandlers();
        this.showResults();
    }

    renderSection(title, items, type) {
        let html = `<div class="search-section">
            <div class="search-section-header">${title} (${items.length})</div>`;

        for (const item of items) {
            const icon = this.getIcon(type);
            const subtitle = this.getSubtitle(item, type);

            html += `
                <div class="search-result-item" data-type="${type}" data-id="${item.id}">
                    <span class="search-result-icon">${icon}</span>
                    <div class="search-result-content">
                        <div class="search-result-title">${item.id}</div>
                        <div class="search-result-subtitle">${subtitle}</div>
                    </div>
                </div>
            `;
        }

        html += '</div>';
        return html;
    }

    getIcon(type) {
        switch (type) {
            case 'agent': return '\u{1F916}';
            case 'artifact': return '\u{1F4E6}';
            case 'event': return '\u{1F4DD}';
            default: return '\u{2753}';
        }
    }

    getSubtitle(item, type) {
        switch (type) {
            case 'agent':
                return `Status: ${item.status} | Scrip: ${item.scrip?.toFixed(2) || '0.00'}`;
            case 'artifact':
                return `Type: ${item.artifact_type} | By: ${item.created_by}`;
            case 'event':
                return `Tick ${item.tick} | ${item.event_type}${item.agent_id ? ' | ' + item.agent_id : ''}`;
            default:
                return '';
        }
    }

    renderError() {
        this.searchResults.innerHTML = `
            <div class="search-error">
                Search failed. Please try again.
            </div>
        `;
        this.showResults();
    }

    attachResultHandlers() {
        const items = this.searchResults.querySelectorAll('.search-result-item');
        items.forEach(item => {
            item.addEventListener('click', () => {
                const type = item.dataset.type;
                const id = item.dataset.id;
                this.handleResultClick(type, id);
            });
        });
    }

    handleResultClick(type, id) {
        this.hideResults();
        this.searchInput.value = '';

        switch (type) {
            case 'agent':
                // Open agent modal
                if (window.AgentsPanel && typeof AgentsPanel.showAgentModal === 'function') {
                    AgentsPanel.showAgentModal(id);
                } else {
                    // Fallback: trigger click on agent row if exists
                    const agentRow = document.querySelector(`#agents-tbody tr[data-agent-id="${id}"]`);
                    if (agentRow) {
                        agentRow.click();
                    }
                }
                break;

            case 'artifact':
                // Open artifact modal
                if (window.ArtifactsPanel && typeof ArtifactsPanel.showArtifactModal === 'function') {
                    ArtifactsPanel.showArtifactModal(id);
                } else {
                    // Fallback: trigger click on artifact row if exists
                    const artifactRow = document.querySelector(`#artifacts-tbody tr[data-artifact-id="${id}"]`);
                    if (artifactRow) {
                        artifactRow.click();
                    }
                }
                break;

            case 'event':
                // Scroll to events panel and highlight
                const eventsPanel = document.querySelector('.events-panel');
                if (eventsPanel) {
                    eventsPanel.scrollIntoView({ behavior: 'smooth' });
                }
                break;
        }
    }

    handleKeydown(e) {
        if (!this.isOpen) return;

        const items = this.searchResults.querySelectorAll('.search-result-item');
        const activeItem = this.searchResults.querySelector('.search-result-item.active');
        let currentIndex = Array.from(items).indexOf(activeItem);

        switch (e.key) {
            case 'ArrowDown':
                e.preventDefault();
                if (currentIndex < items.length - 1) {
                    if (activeItem) activeItem.classList.remove('active');
                    items[currentIndex + 1].classList.add('active');
                    items[currentIndex + 1].scrollIntoView({ block: 'nearest' });
                } else if (currentIndex === -1 && items.length > 0) {
                    items[0].classList.add('active');
                }
                break;

            case 'ArrowUp':
                e.preventDefault();
                if (currentIndex > 0) {
                    if (activeItem) activeItem.classList.remove('active');
                    items[currentIndex - 1].classList.add('active');
                    items[currentIndex - 1].scrollIntoView({ block: 'nearest' });
                }
                break;

            case 'Enter':
                e.preventDefault();
                if (activeItem) {
                    activeItem.click();
                }
                break;
        }
    }

    showResults() {
        this.searchResults.classList.remove('hidden');
        this.isOpen = true;
    }

    hideResults() {
        this.searchResults.classList.add('hidden');
        this.isOpen = false;
    }
}

// Initialize on DOM ready
document.addEventListener('DOMContentLoaded', () => {
    window.globalSearch = new GlobalSearch();
});
