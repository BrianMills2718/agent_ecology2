/**
 * Alerts Manager - Real-time alert banner for dashboard (Plan #145)
 */

const AlertsManager = {
    banner: null,
    content: null,
    dismissBtn: null,
    alerts: [],
    dismissed: false,
    previousState: {
        frozenCount: 0,
        budgetPercent: 0
    },

    init() {
        this.banner = document.getElementById('alerts-banner');
        this.content = document.getElementById('alerts-content');
        this.dismissBtn = document.getElementById('alerts-dismiss');

        if (!this.banner) return;

        // Dismiss handler
        if (this.dismissBtn) {
            this.dismissBtn.addEventListener('click', () => {
                this.dismiss();
            });
        }

        // Listen for KPI updates
        if (window.wsManager) {
            window.wsManager.on('kpi_update', (data) => this.handleKPIUpdate(data));
            window.wsManager.on('state_update', (data) => this.handleStateUpdate(data));
        }
    },

    handleKPIUpdate(data) {
        if (this.dismissed) return;

        const alerts = [];
        const { kpis, health } = data;

        // Check frozen agents
        if (kpis && kpis.frozen_agent_count > 0) {
            const change = kpis.frozen_agent_count - this.previousState.frozenCount;
            if (change > 0) {
                alerts.push({
                    icon: '🥶',
                    text: `${kpis.frozen_agent_count} agent${kpis.frozen_agent_count > 1 ? 's' : ''} frozen${change > 0 ? ` (+${change})` : ''}`,
                    severity: kpis.frozen_agent_count > 3 ? 'critical' : 'warning'
                });
            }
            this.previousState.frozenCount = kpis.frozen_agent_count;
        }

        // Check health warnings
        if (health && health.warnings && health.warnings.length > 0) {
            health.warnings.forEach(warning => {
                alerts.push({
                    icon: '⚠️',
                    text: warning,
                    severity: 'warning'
                });
            });
        }

        this.updateAlerts(alerts);
    },

    handleStateUpdate(data) {
        if (this.dismissed) return;

        const alerts = [];

        // Check API budget
        if (data.progress) {
            const budgetPercent = (data.progress.api_cost_spent / data.progress.api_cost_limit) * 100;

            if (budgetPercent >= 90 && this.previousState.budgetPercent < 90) {
                alerts.push({
                    icon: '💰',
                    text: `API budget ${budgetPercent.toFixed(0)}% consumed`,
                    severity: budgetPercent >= 100 ? 'critical' : 'warning'
                });
            }
            this.previousState.budgetPercent = budgetPercent;
        }

        // Check for frozen agents in agent list
        if (data.agents) {
            const frozenAgents = data.agents.filter(a => a.status === 'frozen');
            if (frozenAgents.length > this.previousState.frozenCount) {
                const newFrozen = frozenAgents.length - this.previousState.frozenCount;
                alerts.push({
                    icon: '🥶',
                    text: `${newFrozen} agent${newFrozen > 1 ? 's' : ''} just froze`,
                    severity: frozenAgents.length > 3 ? 'critical' : 'warning'
                });
            }
            this.previousState.frozenCount = frozenAgents.length;
        }

        if (alerts.length > 0) {
            this.updateAlerts(alerts);
        }
    },

    updateAlerts(alerts) {
        if (alerts.length === 0) {
            this.hide();
            return;
        }

        // Determine highest severity
        const hasCritical = alerts.some(a => a.severity === 'critical');

        // Update banner class
        this.banner.classList.remove('critical');
        if (hasCritical) {
            this.banner.classList.add('critical');
        }

        // Render alerts
        this.content.innerHTML = alerts.map(alert => `
            <span class="alert-item">
                <span class="alert-icon">${alert.icon}</span>
                <span class="alert-text">${alert.text}</span>
            </span>
        `).join('');

        this.show();
    },

    show() {
        this.banner.classList.remove('hidden');
        this.dismissed = false;
    },

    hide() {
        this.banner.classList.add('hidden');
    },

    dismiss() {
        this.hide();
        this.dismissed = true;
        // Reset after 30 seconds so new alerts can appear
        setTimeout(() => {
            this.dismissed = false;
        }, 30000);
    }
};

window.AlertsManager = AlertsManager;
