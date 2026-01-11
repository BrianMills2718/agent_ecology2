/**
 * Simulation controls panel - pause/resume simulation from dashboard
 */

const ControlsPanel = {
    elements: {
        pauseBtn: null,
        resumeBtn: null,
        controlsContainer: null
    },

    isAvailable: false,
    isRunning: false,
    isPaused: false,

    /**
     * Initialize the controls panel
     */
    init() {
        this.elements.pauseBtn = document.getElementById('btn-pause');
        this.elements.resumeBtn = document.getElementById('btn-resume');
        this.elements.controlsContainer = document.getElementById('sim-controls');

        // Button handlers
        if (this.elements.pauseBtn) {
            this.elements.pauseBtn.addEventListener('click', () => this.pause());
        }
        if (this.elements.resumeBtn) {
            this.elements.resumeBtn.addEventListener('click', () => this.resume());
        }

        // Listen for WebSocket control events
        window.wsManager.on('simulation_control', (data) => {
            this.handleControlEvent(data);
        });

        // Check simulation status on connect
        window.wsManager.on('connect', () => {
            this.checkStatus();
        });

        // Initial status check
        this.checkStatus();

        // Periodic status check
        setInterval(() => this.checkStatus(), 5000);
    },

    /**
     * Check simulation status from server
     */
    async checkStatus() {
        try {
            const response = await fetch('/api/simulation/status');
            const status = await response.json();

            this.isAvailable = status.available === true;
            this.isRunning = status.running === true;
            this.isPaused = status.paused === true;

            this.updateUI();
        } catch (error) {
            console.error('Failed to check simulation status:', error);
            this.isAvailable = false;
            this.updateUI();
        }
    },

    /**
     * Handle control events from WebSocket
     */
    handleControlEvent(data) {
        if (data.action === 'paused') {
            this.isPaused = true;
            this.updateUI();
        } else if (data.action === 'resumed') {
            this.isPaused = false;
            this.updateUI();
        }
    },

    /**
     * Update UI to reflect current state
     */
    updateUI() {
        if (!this.elements.pauseBtn || !this.elements.resumeBtn) return;

        if (!this.isAvailable || !this.isRunning) {
            // No simulation available - hide controls
            this.elements.pauseBtn.classList.add('hidden');
            this.elements.resumeBtn.classList.add('hidden');
            return;
        }

        if (this.isPaused) {
            // Show resume button
            this.elements.pauseBtn.classList.add('hidden');
            this.elements.resumeBtn.classList.remove('hidden');
        } else {
            // Show pause button
            this.elements.pauseBtn.classList.remove('hidden');
            this.elements.resumeBtn.classList.add('hidden');
        }
    },

    /**
     * Pause the simulation
     */
    async pause() {
        if (!this.isRunning || this.isPaused) return;

        this.elements.pauseBtn.disabled = true;

        try {
            const response = await fetch('/api/simulation/pause', { method: 'POST' });
            const result = await response.json();

            if (response.ok) {
                this.isPaused = true;
                this.updateUI();
                console.log('Simulation paused at tick', result.tick);
            } else {
                console.error('Failed to pause:', result.detail);
            }
        } catch (error) {
            console.error('Failed to pause simulation:', error);
        } finally {
            this.elements.pauseBtn.disabled = false;
        }
    },

    /**
     * Resume the simulation
     */
    async resume() {
        if (!this.isRunning || !this.isPaused) return;

        this.elements.resumeBtn.disabled = true;

        try {
            const response = await fetch('/api/simulation/resume', { method: 'POST' });
            const result = await response.json();

            if (response.ok) {
                this.isPaused = false;
                this.updateUI();
                console.log('Simulation resumed at tick', result.tick);
            } else {
                console.error('Failed to resume:', result.detail);
            }
        } catch (error) {
            console.error('Failed to resume simulation:', error);
        } finally {
            this.elements.resumeBtn.disabled = false;
        }
    }
};

window.ControlsPanel = ControlsPanel;
