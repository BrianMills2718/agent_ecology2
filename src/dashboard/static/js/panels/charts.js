/**
 * Resource utilization charts panel
 */

const ChartsPanel = {
    elements: {
        canvas: null,
        tabBtns: null
    },

    chart: null,
    currentChart: 'compute',
    chartData: {
        compute: null,
        scrip: null,
        flow: null
    },

    colors: [
        'rgba(233, 69, 96, 0.8)',   // Red
        'rgba(15, 76, 117, 0.8)',   // Blue
        'rgba(76, 175, 80, 0.8)',   // Green
        'rgba(255, 152, 0, 0.8)',   // Orange
        'rgba(156, 39, 176, 0.8)',  // Purple
        'rgba(0, 188, 212, 0.8)',   // Cyan
    ],

    /**
     * Initialize the charts panel
     */
    init() {
        this.elements.canvas = document.getElementById('resource-chart');
        this.elements.tabBtns = document.querySelectorAll('.chart-tabs .tab-btn');

        // Tab button handlers
        this.elements.tabBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                this.switchChart(btn.dataset.chart);
            });
        });

        // Initialize empty chart
        this.createChart();

        // Listen for updates
        window.wsManager.on('initial_state', () => {
            this.loadAll();
        });

        window.wsManager.on('state_update', () => {
            // Reload current chart data on state update
            this.loadCurrent();
        });
    },

    /**
     * Create the Chart.js chart
     */
    createChart() {
        if (!this.elements.canvas) return;

        const ctx = this.elements.canvas.getContext('2d');

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [],
                datasets: []
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Tick',
                            color: '#a0a0a0'
                        },
                        ticks: { color: '#a0a0a0' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Value',
                            color: '#a0a0a0'
                        },
                        ticks: { color: '#a0a0a0' },
                        grid: { color: 'rgba(255,255,255,0.1)' }
                    }
                },
                plugins: {
                    legend: {
                        labels: { color: '#eaeaea' }
                    }
                }
            }
        });
    },

    /**
     * Switch to a different chart type
     */
    switchChart(chartType) {
        this.currentChart = chartType;

        // Update tab buttons
        this.elements.tabBtns.forEach(btn => {
            btn.classList.toggle('active', btn.dataset.chart === chartType);
        });

        // Update chart display
        this.updateChart();
    },

    /**
     * Update the chart with current data
     */
    updateChart() {
        if (!this.chart) return;

        const data = this.chartData[this.currentChart];
        if (!data) {
            this.chart.data.labels = [];
            this.chart.data.datasets = [];
            this.chart.update();
            return;
        }

        // Get all ticks (x-axis labels)
        const allTicks = new Set();
        data.agents.forEach(agent => {
            agent.data.forEach(point => allTicks.add(point.tick));
        });
        data.totals.forEach(point => allTicks.add(point.tick));

        const sortedTicks = Array.from(allTicks).sort((a, b) => a - b);
        this.chart.data.labels = sortedTicks;

        // Create datasets for each agent
        const datasets = data.agents.map((agent, index) => {
            const color = this.colors[index % this.colors.length];
            const dataMap = new Map(agent.data.map(p => [p.tick, p.value]));

            return {
                label: agent.agent_id,
                data: sortedTicks.map(tick => dataMap.get(tick) || 0),
                borderColor: color,
                backgroundColor: color.replace('0.8', '0.2'),
                fill: false,
                tension: 0.1
            };
        });

        // Add total line if available
        if (data.totals.length > 0) {
            const totalMap = new Map(data.totals.map(p => [p.tick, p.value]));
            datasets.push({
                label: 'Total',
                data: sortedTicks.map(tick => totalMap.get(tick) || 0),
                borderColor: 'rgba(255, 255, 255, 0.8)',
                backgroundColor: 'rgba(255, 255, 255, 0.2)',
                borderDash: [5, 5],
                fill: false,
                tension: 0.1
            });
        }

        this.chart.data.datasets = datasets;

        // Update y-axis label
        const yLabel = this.currentChart === 'compute' ? 'Compute Used'
            : this.currentChart === 'scrip' ? 'Scrip Balance'
            : 'Value';
        this.chart.options.scales.y.title.text = yLabel;

        this.chart.update();
    },

    /**
     * Load all chart data
     */
    async loadAll() {
        await Promise.all([
            this.loadCompute(),
            this.loadScrip(),
            this.loadFlow()
        ]);
        this.updateChart();
    },

    /**
     * Load current chart data
     */
    async loadCurrent() {
        switch (this.currentChart) {
            case 'compute':
                await this.loadCompute();
                break;
            case 'scrip':
                await this.loadScrip();
                break;
            case 'flow':
                await this.loadFlow();
                break;
        }
        this.updateChart();
    },

    /**
     * Load compute chart data
     */
    async loadCompute() {
        try {
            this.chartData.compute = await API.getComputeChart();
        } catch (error) {
            console.error('Failed to load compute chart:', error);
        }
    },

    /**
     * Load scrip chart data
     */
    async loadScrip() {
        try {
            this.chartData.scrip = await API.getScripChart();
        } catch (error) {
            console.error('Failed to load scrip chart:', error);
        }
    },

    /**
     * Load flow chart data
     */
    async loadFlow() {
        try {
            const flowData = await API.getFlowChart();
            // Convert flow data to chart format
            // For now, show transfers as cumulative
            this.chartData.flow = {
                agents: [],
                totals: []
            };
        } catch (error) {
            console.error('Failed to load flow chart:', error);
        }
    }
};

window.ChartsPanel = ChartsPanel;
