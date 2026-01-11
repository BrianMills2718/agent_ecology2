/**
 * WebSocket connection manager for real-time updates
 */

class WebSocketManager {
    constructor() {
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 10;
        this.reconnectDelay = 1000;
        this.listeners = {
            event: [],
            state_update: [],
            initial_state: [],
            connect: [],
            disconnect: []
        };
        this.pingInterval = null;
    }

    /**
     * Connect to the WebSocket server
     */
    connect() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                this.updateStatusIndicator(true);
                this.emit('connect');
                this.startPing();
            };

            this.ws.onmessage = (event) => {
                this.handleMessage(event.data);
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.updateStatusIndicator(false);
                this.emit('disconnect');
                this.stopPing();
                this.scheduleReconnect();
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
            };

        } catch (error) {
            console.error('Failed to create WebSocket:', error);
            this.scheduleReconnect();
        }
    }

    /**
     * Handle incoming WebSocket message
     */
    handleMessage(data) {
        // Handle ping/pong
        if (data === 'ping') {
            this.ws.send('pong');
            return;
        }
        if (data === 'pong') {
            return;
        }

        try {
            const message = JSON.parse(data);
            const type = message.type;

            if (this.listeners[type]) {
                this.listeners[type].forEach(callback => {
                    try {
                        callback(message.data);
                    } catch (error) {
                        console.error('Listener error:', error);
                    }
                });
            }
        } catch (error) {
            console.error('Failed to parse WebSocket message:', error);
        }
    }

    /**
     * Add event listener
     */
    on(eventType, callback) {
        if (!this.listeners[eventType]) {
            this.listeners[eventType] = [];
        }
        this.listeners[eventType].push(callback);
    }

    /**
     * Remove event listener
     */
    off(eventType, callback) {
        if (this.listeners[eventType]) {
            this.listeners[eventType] = this.listeners[eventType].filter(
                cb => cb !== callback
            );
        }
    }

    /**
     * Emit event to listeners
     */
    emit(eventType, data) {
        if (this.listeners[eventType]) {
            this.listeners[eventType].forEach(callback => {
                try {
                    callback(data);
                } catch (error) {
                    console.error('Listener error:', error);
                }
            });
        }
    }

    /**
     * Schedule reconnection attempt
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.log('Max reconnect attempts reached');
            return;
        }

        this.reconnectAttempts++;
        const delay = this.reconnectDelay * Math.pow(1.5, this.reconnectAttempts - 1);
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

        setTimeout(() => {
            this.connect();
        }, delay);
    }

    /**
     * Start ping interval for keepalive
     */
    startPing() {
        this.pingInterval = setInterval(() => {
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 25000);
    }

    /**
     * Stop ping interval
     */
    stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    /**
     * Update connection status indicator in UI
     */
    updateStatusIndicator(connected) {
        const indicator = document.getElementById('ws-status');
        const text = document.getElementById('ws-status-text');

        if (indicator) {
            indicator.classList.toggle('connected', connected);
            indicator.classList.toggle('disconnected', !connected);
        }

        if (text) {
            text.textContent = connected ? 'Connected' : 'Disconnected';
        }
    }

    /**
     * Send a message (if needed for future features)
     */
    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
        }
    }

    /**
     * Disconnect
     */
    disconnect() {
        this.stopPing();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Create global instance
window.wsManager = new WebSocketManager();
