// Global variables
let currentPeriod = 'today';
let powerChart = null;
let liveDataInterval = null;
let optimizationInterval = null;

// API base URL
const API_BASE = 'http://localhost:8000';

// Initialize the application
document.addEventListener('DOMContentLoaded', function() {
    initializeChart();
    setupEventListeners();
    startLiveUpdates();
    loadOptimizationData();
    updateMonthlyUnits();
});

// Setup event listeners
function setupEventListeners() {
    const chartButtons = document.querySelectorAll('.chart-btn');
    chartButtons.forEach(btn => {
        btn.addEventListener('click', function() {
            // Remove active class from all buttons
            chartButtons.forEach(b => b.classList.remove('active'));
            // Add active class to clicked button
            this.classList.add('active');
            // Update current period
            currentPeriod = this.dataset.period;
            // Update chart
            updateChart();
        });
    });
}

// Initialize chart
function initializeChart() {
    const canvas = document.getElementById('powerChart');
    const ctx = canvas.getContext('2d');
    
    // Create gradient
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(30, 64, 175, 0.3)');
    gradient.addColorStop(1, 'rgba(30, 64, 175, 0.05)');
    
    powerChart = {
        canvas: canvas,
        ctx: ctx,
        gradient: gradient
    };
    
    updateChart();
}

// Update chart with new data
async function updateChart() {
    try {
        const response = await fetch(`${API_BASE}/power-data/${currentPeriod}`);
        const rawData = await response.json();

        const canvas = powerChart.canvas;
        const ctx = powerChart.ctx;

        ctx.clearRect(0, 0, canvas.width, canvas.height);

        if (rawData.length === 0) {
            drawNoDataMessage(ctx, canvas);
            return;
        }

        // Grouping logic
        const grouped = [];
        const now = new Date();
        const slotMap = {};

        if (currentPeriod === 'today') {
            for (let i = 0; i < 8; i++) slotMap[i] = [];
            rawData.forEach(entry => {
                const timestamp = new Date(entry.timestamp);
                const hoursAgo = (now - timestamp) / (1000 * 60 * 60);
                if (hoursAgo <= 24) {
                    const slot = 7 - Math.floor(hoursAgo / 3);
                    if (slot >= 0 && slot <= 7) slotMap[slot].push(entry.power);
                }
            });
            for (let i = 0; i < 8; i++) {
                const avg = slotMap[i].length ? slotMap[i].reduce((a, b) => a + b, 0) / slotMap[i].length : 0;
                grouped.push({ power: avg, label: `${i * 3}-${(i + 1) * 3}h` });
            }
        } else if (currentPeriod === 'week') {
            for (let i = 0; i < 7; i++) slotMap[i] = [];
            rawData.forEach(entry => {
                const timestamp = new Date(entry.timestamp);
                const daysAgo = Math.floor((now - timestamp) / (1000 * 60 * 60 * 24));
                const slot = 6 - daysAgo;
                if (slot >= 0 && slot <= 6) slotMap[slot].push(entry.power);
            });
            for (let i = 0; i < 7; i++) {
                const avg = slotMap[i].length ? slotMap[i].reduce((a, b) => a + b, 0) / slotMap[i].length : 0;
                grouped.push({ power: avg, label: `Day ${i + 1}` });
            }
        } else if (currentPeriod === 'month') {
            for (let i = 0; i < 10; i++) slotMap[i] = [];
            rawData.forEach(entry => {
                const timestamp = new Date(entry.timestamp);
                const daysAgo = Math.floor((now - timestamp) / (1000 * 60 * 60 * 24));
                const slot = 9 - Math.floor(daysAgo / 3);
                if (slot >= 0 && slot <= 9) slotMap[slot].push(entry.power);
            });
            for (let i = 0; i < 10; i++) {
                const avg = slotMap[i].length ? slotMap[i].reduce((a, b) => a + b, 0) / slotMap[i].length : 0;
                grouped.push({ power: avg, label: `Day ${i * 3 + 1}-${(i + 1) * 3}` });
            }
        }

        drawChart(ctx, canvas, grouped);

    } catch (error) {
        console.error('Error fetching chart data:', error);
        drawErrorMessage(powerChart.ctx, powerChart.canvas);
    }
}

// Draw chart function
function drawChart(ctx, canvas, data) {
    const padding = 60;
    const width = canvas.width - 2 * padding;
    const height = canvas.height - 2 * padding;

    if (data.length === 0) return;

    const values = data.map(d => d.power);
    const minValue = Math.min(...values);
    const maxValue = Math.max(...values);
    const valueRange = maxValue - minValue || 1;

    // Grid lines
    ctx.strokeStyle = '#e5e7eb';
    ctx.lineWidth = 1;

    for (let i = 0; i <= 5; i++) {
        const y = padding + (height * i) / 5;
        ctx.beginPath();
        ctx.moveTo(padding, y);
        ctx.lineTo(padding + width, y);
        ctx.stroke();
    }

    for (let i = 0; i <= data.length; i++) {
        const x = padding + (width * i) / data.length;
        ctx.beginPath();
        ctx.moveTo(x, padding);
        ctx.lineTo(x, padding + height);
        ctx.stroke();
    }

    // Area
    ctx.fillStyle = powerChart.gradient;
    ctx.beginPath();
    ctx.moveTo(padding, padding + height);

    data.forEach((point, index) => {
        const x = padding + (width * index) / (data.length - 1);
        const y = padding + height - ((point.power - minValue) / valueRange) * height;
        ctx.lineTo(x, y);
    });

    ctx.lineTo(padding + width, padding + height);
    ctx.closePath();
    ctx.fill();

    // Line
    ctx.strokeStyle = '#1e40af';
    ctx.lineWidth = 3;
    ctx.beginPath();
    data.forEach((point, index) => {
        const x = padding + (width * index) / (data.length - 1);
        const y = padding + height - ((point.power - minValue) / valueRange) * height;
        if (index === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
    });
    ctx.stroke();

    // Points
    ctx.fillStyle = '#facc15';
    data.forEach((point, index) => {
        const x = padding + (width * index) / (data.length - 1);
        const y = padding + height - ((point.power - minValue) / valueRange) * height;
        ctx.beginPath();
        ctx.arc(x, y, 4, 0, 2 * Math.PI);
        ctx.fill();
    });

    // Labels
    ctx.fillStyle = '#64748b';
    ctx.font = '12px Segoe UI';
    ctx.textAlign = 'center';

    // Y-axis
    ctx.textAlign = 'right';
    for (let i = 0; i <= 5; i++) {
        const value = minValue + (valueRange * (5 - i)) / 5;
        const y = padding + (height * i) / 5;
        ctx.fillText(Math.round(value) + 'W', padding - 10, y + 4);
    }

    // X-axis
    ctx.textAlign = 'center';
    data.forEach((point, index) => {
        const x = padding + (width * index) / (data.length - 1);
        ctx.fillText(point.label, x, padding + height + 20);
    });
}


// Draw no data message
function drawNoDataMessage(ctx, canvas) {
    ctx.fillStyle = '#64748b';
    ctx.font = '16px Segoe UI';
    ctx.textAlign = 'center';
    ctx.fillText('No data available for selected period', canvas.width / 2, canvas.height / 2);
}

// Draw error message
function drawErrorMessage(ctx, canvas) {
    ctx.fillStyle = '#ef4444';
    ctx.font = '16px Segoe UI';
    ctx.textAlign = 'center';
    ctx.fillText('Error loading chart data', canvas.width / 2, canvas.height / 2);
}

// Start live data updates
function startLiveUpdates() {
    updateLiveMetrics();
    liveDataInterval = setInterval(updateLiveMetrics, 10000); // Update every 10 seconds
}

// Update live metrics
async function updateLiveMetrics() {
    try {
        const response = await fetch(`${API_BASE}/live-data`);
        const data = await response.json();
        
        document.getElementById('liveVoltage').textContent = data.voltage?.toFixed(1) || '--';
        document.getElementById('liveCurrent').textContent = data.current?.toFixed(2) || '--';
        document.getElementById('livePower').textContent = data.power?.toFixed(0) || '--';
        
    } catch (error) {
        console.error('Error fetching live data:', error);
        document.getElementById('liveVoltage').textContent = '--';
        document.getElementById('liveCurrent').textContent = '--';
        document.getElementById('livePower').textContent = '--';
    }
}

// Update monthly units
async function updateMonthlyUnits() {
    try {
        const response = await fetch(`${API_BASE}/monthly-units`);
        const data = await response.json();
        
        document.getElementById('monthlyUnits').textContent = data.units?.toFixed(2) || '0';
        
    } catch (error) {
        console.error('Error fetching monthly units:', error);
        document.getElementById('monthlyUnits').textContent = '0';
    }
}

// Load optimization data
async function loadOptimizationData() {
    updateOptimizationRecommendations();
    optimizationInterval = setInterval(updateOptimizationRecommendations, 60000); // Update every minute
}

// Update optimization recommendations
async function updateOptimizationRecommendations() {
    try {
        // Slot recommendations
        const slotResponse = await fetch(`${API_BASE}/slot-recommendations`);
        const slotData = await slotResponse.json();
        
        const slotElement = document.getElementById('slotRecommendation');
        if (slotData.recommendations && slotData.recommendations.length > 0) {
            slotElement.innerHTML = slotData.recommendations.map(rec => 
                `<div class="recommendation-item">
                    <strong>${rec.time_slot}</strong>: ${rec.recommendation}
                    <br><small>Potential savings: ₹${rec.savings?.toFixed(2) || '0'}</small>
                </div>`
            ).join('');
        } else {
            slotElement.innerHTML = '<div class="loading">No recommendations available</div>';
        }
        
        // Peak detection
        const peakResponse = await fetch(`${API_BASE}/peak-detection`);
        const peakData = await peakResponse.json();
        
        const peakElement = document.getElementById('peakDetection');
        if (peakData.peaks && peakData.peaks.length > 0) {
            peakElement.innerHTML = peakData.peaks.map(peak => 
                `<div class="recommendation-item">
                    <strong>Peak detected at ${new Date(peak.timestamp).toLocaleTimeString()}</strong>
                    <br>Power: ${peak.power}W
                    <br><small>${peak.suggestion}</small>
                </div>`
            ).join('');
        } else {
            peakElement.innerHTML = '<div class="loading">No peaks detected</div>';
        }
        
    } catch (error) {
        console.error('Error fetching optimization data:', error);
        document.getElementById('slotRecommendation').innerHTML = '<div class="loading">Error loading recommendations</div>';
        document.getElementById('peakDetection').innerHTML = '<div class="loading">Error loading peak detection</div>';
    }
}

// Cleanup intervals when page unloads
window.addEventListener('beforeunload', function() {
    if (liveDataInterval) clearInterval(liveDataInterval);
    if (optimizationInterval) clearInterval(optimizationInterval);
});