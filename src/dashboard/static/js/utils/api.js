/**
 * REST API client for the dashboard
 */

const API = {
    baseUrl: '',

    /**
     * Make a GET request to the API
     */
    async get(endpoint) {
        try {
            const response = await fetch(`${this.baseUrl}${endpoint}`);
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return await response.json();
        } catch (error) {
            console.error(`API error on ${endpoint}:`, error);
            throw error;
        }
    },

    /**
     * Get complete simulation state
     */
    async getState() {
        return this.get('/api/state');
    },

    /**
     * Get simulation progress only
     */
    async getProgress() {
        return this.get('/api/progress');
    },

    /**
     * Get all agents
     */
    async getAgents() {
        return this.get('/api/agents');
    },

    /**
     * Get single agent details
     */
    async getAgent(agentId) {
        return this.get(`/api/agents/${encodeURIComponent(agentId)}`);
    },

    /**
     * Get agent configuration from YAML (Plan #108)
     */
    async getAgentConfig(agentId) {
        return this.get(`/api/agents/${encodeURIComponent(agentId)}/config`);
    },

    /**
     * Get all artifacts
     */
    async getArtifacts() {
        return this.get('/api/artifacts');
    },

    /**
     * Get filtered events
     */
    async getEvents(options = {}) {
        const params = new URLSearchParams();
        if (options.eventTypes) {
            params.set('event_types', options.eventTypes.join(','));
        }
        if (options.agentId) {
            params.set('agent_id', options.agentId);
        }
        if (options.artifactId) {
            params.set('artifact_id', options.artifactId);
        }
        if (options.tickMin !== undefined) {
            params.set('tick_min', options.tickMin);
        }
        if (options.tickMax !== undefined) {
            params.set('tick_max', options.tickMax);
        }
        if (options.limit) {
            params.set('limit', options.limit);
        }
        if (options.offset) {
            params.set('offset', options.offset);
        }
        const query = params.toString();
        return this.get(`/api/events${query ? '?' + query : ''}`);
    },

    /**
     * Get genesis activity
     */
    async getGenesis() {
        return this.get('/api/genesis');
    },

    /**
     * Get compute chart data
     */
    async getComputeChart() {
        return this.get('/api/charts/compute');
    },

    /**
     * Get scrip chart data
     */
    async getScripChart() {
        return this.get('/api/charts/scrip');
    },

    /**
     * Get flow chart data
     */
    async getFlowChart() {
        return this.get('/api/charts/flow');
    },

    /**
     * Get simulation config
     */
    async getConfig() {
        return this.get('/api/config');
    },

    /**
     * Get tick summaries
     */
    async getTicks() {
        return this.get('/api/ticks');
    }
};

// Export for use by other modules
window.API = API;
