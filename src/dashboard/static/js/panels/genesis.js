/**
 * Genesis artifacts activity panel
 */

const GenesisPanel = {
    elements: {
        tabs: null,
        tabContents: null,
        oraclePending: null,
        oracleMinted: null,
        oracleScores: null,
        escrowActive: null,
        escrowListings: null,
        ledgerTransferCount: null,
        ledgerTransfers: null
    },

    genesisData: null,

    /**
     * Initialize the genesis panel
     */
    init() {
        this.elements.tabs = document.querySelectorAll('.genesis-tab');
        this.elements.tabContents = document.querySelectorAll('.genesis-tab-content');
        this.elements.oraclePending = document.getElementById('oracle-pending');
        this.elements.oracleMinted = document.getElementById('oracle-minted');
        this.elements.oracleScores = document.getElementById('oracle-scores');
        this.elements.escrowActive = document.getElementById('escrow-active');
        this.elements.escrowListings = document.getElementById('escrow-listings');
        this.elements.ledgerTransferCount = document.getElementById('ledger-transfer-count');
        this.elements.ledgerTransfers = document.getElementById('ledger-transfers');

        // Tab handlers
        this.elements.tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                this.switchTab(tab.dataset.tab);
            });
        });

        // Listen for updates
        window.wsManager.on('initial_state', () => {
            this.load();
        });

        window.wsManager.on('state_update', () => {
            this.load();
        });

        window.wsManager.on('event', (event) => {
            // Quick update for specific events
            if (event.event_type === 'mint') {
                this.load();
            }
        });
    },

    /**
     * Switch to a different tab
     */
    switchTab(tabName) {
        this.elements.tabs.forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        this.elements.tabContents.forEach(content => {
            content.classList.toggle('active', content.id === `genesis-${tabName}`);
        });
    },

    /**
     * Update all genesis data
     */
    update(data) {
        this.genesisData = data;

        // Oracle tab
        if (data.oracle) {
            if (this.elements.oraclePending) {
                this.elements.oraclePending.textContent = data.oracle.pending_count;
            }
            if (this.elements.oracleMinted) {
                this.elements.oracleMinted.textContent = data.oracle.total_scrip_minted;
            }
            if (this.elements.oracleScores) {
                this.renderOracleScores(data.oracle.recent_scores);
            }
        }

        // Escrow tab
        if (data.escrow) {
            if (this.elements.escrowActive) {
                this.elements.escrowActive.textContent = data.escrow.active_listings.length;
            }
            if (this.elements.escrowListings) {
                this.renderEscrowListings(data.escrow.active_listings);
            }
        }

        // Ledger tab
        if (data.ledger) {
            if (this.elements.ledgerTransferCount) {
                this.elements.ledgerTransferCount.textContent = data.ledger.recent_transfers.length;
            }
            if (this.elements.ledgerTransfers) {
                this.renderLedgerTransfers(data.ledger.recent_transfers);
            }
        }
    },

    /**
     * Render oracle scores list
     */
    renderOracleScores(scores) {
        if (!this.elements.oracleScores) return;

        if (!scores || scores.length === 0) {
            this.elements.oracleScores.innerHTML = '<div class="genesis-list-item">No scores yet</div>';
            return;
        }

        this.elements.oracleScores.innerHTML = scores.slice(-10).reverse().map(score => `
            <div class="genesis-list-item">
                <strong>${this.escapeHtml(score.artifact_id)}</strong>:
                ${score.score.toFixed(1)} -> ${score.scrip_minted} scrip
            </div>
        `).join('');
    },

    /**
     * Render escrow listings
     */
    renderEscrowListings(listings) {
        if (!this.elements.escrowListings) return;

        if (!listings || listings.length === 0) {
            this.elements.escrowListings.innerHTML = '<div class="genesis-list-item">No active listings</div>';
            return;
        }

        this.elements.escrowListings.innerHTML = listings.map(listing => `
            <div class="genesis-list-item">
                <strong>${this.escapeHtml(listing.artifact_id)}</strong>:
                ${listing.price} scrip (from ${this.escapeHtml(listing.seller_id)})
            </div>
        `).join('');
    },

    /**
     * Render ledger transfers
     */
    renderLedgerTransfers(transfers) {
        if (!this.elements.ledgerTransfers) return;

        if (!transfers || transfers.length === 0) {
            this.elements.ledgerTransfers.innerHTML = '<div class="genesis-list-item">No transfers yet</div>';
            return;
        }

        this.elements.ledgerTransfers.innerHTML = transfers.slice(-10).reverse().map(transfer => `
            <div class="genesis-list-item">
                ${this.escapeHtml(transfer.from_id)} -> ${this.escapeHtml(transfer.to_id)}:
                ${transfer.amount} scrip
            </div>
        `).join('');
    },

    /**
     * Load genesis data from API
     */
    async load() {
        try {
            const data = await API.getGenesis();
            this.update(data);
        } catch (error) {
            console.error('Failed to load genesis data:', error);
        }
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

window.GenesisPanel = GenesisPanel;
