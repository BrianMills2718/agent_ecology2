/**
 * Agent Thinking Panel - Display agent reasoning and thought processes
 */

class ThinkingPanel {
    constructor() {
        this.container = null;
        this.thinkingList = null;
        this.agentFilter = null;
        this.currentAgent = null;
        this.expandedItems = new Set();
    }

    init() {
        this.container = document.getElementById('thinking-panel');
        if (!this.container) return;

        this.thinkingList = document.getElementById('thinking-list');
        this.agentFilter = document.getElementById('thinking-agent-filter');

        // Set up agent filter
        if (this.agentFilter) {
            this.agentFilter.addEventListener('change', () => {
                this.currentAgent = this.agentFilter.value || null;
                this.refresh();
            });
        }

        // Initial load
        this.refresh();
    }

    async refresh() {
        if (!this.thinkingList) return;

        try {
            let url = '/api/thinking?limit=50';
            if (this.currentAgent) {
                url += `&agent_id=${encodeURIComponent(this.currentAgent)}`;
            }

            const response = await fetch(url);
            const data = await response.json();

            this.render(data.items);
            this.updateAgentFilter();
        } catch (error) {
            console.error('Failed to load thinking history:', error);
        }
    }

    async updateAgentFilter() {
        if (!this.agentFilter) return;

        try {
            const response = await fetch('/api/agents');
            const agents = await response.json();

            // Preserve current selection
            const currentValue = this.agentFilter.value;

            this.agentFilter.innerHTML = '<option value="">All Agents</option>';
            agents.forEach(agent => {
                const option = document.createElement('option');
                option.value = agent.agent_id;
                option.textContent = agent.agent_id;
                if (agent.agent_id === currentValue) {
                    option.selected = true;
                }
                this.agentFilter.appendChild(option);
            });
        } catch (error) {
            console.error('Failed to load agents for filter:', error);
        }
    }

    render(items) {
        if (!this.thinkingList) return;

        if (!items || items.length === 0) {
            this.thinkingList.innerHTML = `
                <div class="empty-state">
                    <p>No agent thinking recorded yet.</p>
                    <p class="muted">Agent reasoning will appear here as they think.</p>
                </div>
            `;
            return;
        }

        this.thinkingList.innerHTML = items.map(item => this.renderThinkingItem(item)).join('');

        // Attach click handlers for expand/collapse
        this.thinkingList.querySelectorAll('.thinking-item').forEach(el => {
            el.addEventListener('click', (e) => {
                if (e.target.closest('.thinking-content')) return; // Don't toggle when clicking content
                this.toggleExpand(el);
            });
        });
    }

    renderThinkingItem(item) {
        const itemId = `thinking-${item.agent_id}-${item.tick}`;
        const isExpanded = this.expandedItems.has(itemId);

        // Plan #88: Check for OODA mode (has situation_assessment and action_rationale)
        const isOODAMode = item.situation_assessment && item.action_rationale;
        const hasContent = isOODAMode || (item.thought_process && item.thought_process.trim());

        // Truncate for preview - use action_rationale in OODA mode as it's already concise
        let preview = '';
        if (isOODAMode) {
            preview = item.action_rationale.substring(0, 100);
            if (item.action_rationale.length > 100) preview += '...';
        } else if (item.thought_process) {
            preview = item.thought_process.substring(0, 100);
            if (item.thought_process.length > 100) preview += '...';
        }

        // Render content based on mode
        let contentHtml = '';
        if (isOODAMode) {
            // OODA mode: Show structured fields
            contentHtml = `
                <div class="thinking-content ${isExpanded ? '' : 'hidden'}">
                    <div class="ooda-section">
                        <div class="ooda-label">Situation Assessment</div>
                        <pre class="ooda-text">${this.escapeHtml(item.situation_assessment)}</pre>
                    </div>
                    <div class="ooda-section">
                        <div class="ooda-label">Action Rationale</div>
                        <pre class="ooda-text ooda-rationale">${this.escapeHtml(item.action_rationale)}</pre>
                    </div>
                </div>
            `;
        } else if (item.thought_process) {
            // Simple mode: Show thought_process
            contentHtml = `
                <div class="thinking-content ${isExpanded ? '' : 'hidden'}">
                    <pre>${this.escapeHtml(item.thought_process)}</pre>
                </div>
            `;
        }

        return `
            <div class="thinking-item ${isExpanded ? 'expanded' : ''} ${isOODAMode ? 'ooda-mode' : ''}" data-id="${itemId}">
                <div class="thinking-header">
                    <span class="thinking-agent">${this.escapeHtml(item.agent_id)}</span>
                    <span class="thinking-tick">Tick ${item.tick}</span>
                    <span class="thinking-tokens">${item.input_tokens} in / ${item.output_tokens} out</span>
                    <span class="thinking-cost">${item.thinking_cost} compute</span>
                    ${isOODAMode ? '<span class="ooda-badge">OODA</span>' : ''}
                    ${hasContent ? '<span class="expand-icon">&#x25BC;</span>' : ''}
                </div>
                ${hasContent ? `
                    <div class="thinking-preview ${isExpanded ? 'hidden' : ''}">${this.escapeHtml(preview)}</div>
                    ${contentHtml}
                ` : `
                    <div class="thinking-no-content">No reasoning content recorded</div>
                `}
            </div>
        `;
    }

    toggleExpand(element) {
        const itemId = element.dataset.id;
        const preview = element.querySelector('.thinking-preview');
        const content = element.querySelector('.thinking-content');
        const icon = element.querySelector('.expand-icon');

        if (!content) return;

        if (this.expandedItems.has(itemId)) {
            this.expandedItems.delete(itemId);
            element.classList.remove('expanded');
            if (preview) preview.classList.remove('hidden');
            content.classList.add('hidden');
            if (icon) icon.innerHTML = '&#x25BC;'; // Down arrow
        } else {
            this.expandedItems.add(itemId);
            element.classList.add('expanded');
            if (preview) preview.classList.add('hidden');
            content.classList.remove('hidden');
            if (icon) icon.innerHTML = '&#x25B2;'; // Up arrow
        }
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    onEvent(event) {
        // Refresh when we get a thinking event
        if (event.event_type === 'thinking') {
            this.refresh();
        }
    }
}

// Export for use in main.js
window.ThinkingPanel = ThinkingPanel;
