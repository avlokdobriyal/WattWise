// Global variables
let applianceDataInterval = null;
let recommendationsInterval = null;

// API base URL
const API_BASE = 'http://localhost:8000';

// Initialize dashboard
document.addEventListener('DOMContentLoaded', function() {
    startApplianceUpdates();
    startRecommendationUpdates();
});

// Start appliance data updates
function startApplianceUpdates() {
    updateApplianceData();
    applianceDataInterval = setInterval(updateApplianceData, 10000); // Update every 10 seconds
}

// Update appliance data
async function updateApplianceData() {
    const appliances = ['fridge', 'ac', 'geyser', 'microwave'];
    
    for (const appliance of appliances) {
        try {
            const response = await fetch(`${API_BASE}/appliance-data/${appliance}`);
            const data = await response.json();
            
            document.getElementById(`${appliance}Voltage`).textContent = data.voltage?.toFixed(1) || '--';
            document.getElementById(`${appliance}Current`).textContent = data.current?.toFixed(2) || '--';
            document.getElementById(`${appliance}Power`).textContent = data.power?.toFixed(0) || '--';
            
        } catch (error) {
            console.error(`Error fetching ${appliance} data:`, error);
            document.getElementById(`${appliance}Voltage`).textContent = '--';
            document.getElementById(`${appliance}Current`).textContent = '--';
            document.getElementById(`${appliance}Power`).textContent = '--';
        }
    }
}

// Start recommendation updates
function startRecommendationUpdates() {
    updateLiveRecommendations();
    recommendationsInterval = setInterval(updateLiveRecommendations, 30000); // Update every 30 seconds
}

// Update live recommendations
async function updateLiveRecommendations() {
    try {
        const response = await fetch(`${API_BASE}/live-recommendations`);
        const data = await response.json();
        
        const container = document.getElementById('liveRecommendations');
        
        if (data.recommendations && data.recommendations.length > 0) {
            container.innerHTML = data.recommendations.map(rec => 
                `<div class="recommendation-item">
                    <h4>${rec.title}</h4>
                    <p>${rec.description}</p>
                    ${rec.savings ? `<small style="color: #10b981; font-weight: 600;">Potential savings: ₹${rec.savings.toFixed(2)}</small>` : ''}
                </div>`
            ).join('');
        } else {
            container.innerHTML = '<div class="loading">Analyzing data for recommendations...</div>';
        }
        
    } catch (error) {
        console.error('Error fetching live recommendations:', error);
        document.getElementById('liveRecommendations').innerHTML = 
            '<div class="loading">Error loading recommendations</div>';
    }
}

// Calculate single rate bill
async function calculateSingleBill() {
    const rate = parseFloat(document.getElementById('singleRate').value);
    
    if (!rate || rate <= 0) {
        document.getElementById('singleBillResult').innerHTML = 
            '<span style="color: #ef4444;">Please enter a valid rate</span>';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/monthly-units`);
        const data = await response.json();
        
        const units = data.units || 0;
        const totalBill = units * rate;
        
        document.getElementById('singleBillResult').innerHTML = 
            `<div style="color: #1e40af;">
                <strong>Monthly Units:</strong> ${units.toFixed(2)} kWh<br>
                <strong>Rate:</strong> ₹${rate.toFixed(2)} per kWh<br>
                <strong>Total Bill:</strong> ₹${totalBill.toFixed(2)}
            </div>`;
            
    } catch (error) {
        console.error('Error calculating single bill:', error);
        document.getElementById('singleBillResult').innerHTML = 
            '<span style="color: #ef4444;">Error calculating bill</span>';
    }
}

// Calculate variable rate bill
async function calculateVariableBill() {
    const peakRate = parseFloat(document.getElementById('peakRate').value);
    const standardRate = parseFloat(document.getElementById('standardRate').value);
    const offPeakRate = parseFloat(document.getElementById('offPeakRate').value);
    
    if (!peakRate || !standardRate || !offPeakRate || 
        peakRate <= 0 || standardRate <= 0 || offPeakRate <= 0) {
        document.getElementById('variableBillResult').innerHTML = 
            '<span style="color: #ef4444;">Please enter valid rates for all time slots</span>';
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE}/variable-billing`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                peak_rate: peakRate,
                standard_rate: standardRate,
                off_peak_rate: offPeakRate
            })
        });
        
        const data = await response.json();
        
        document.getElementById('variableBillResult').innerHTML = 
            `<div style="color: #1e40af;">
                <strong>Peak Hours (9AM-6PM):</strong> ${data.peak_units.toFixed(2)} kWh × ₹${peakRate.toFixed(2)} = ₹${data.peak_cost.toFixed(2)}<br>
                <strong>Standard Hours (6PM-10PM):</strong> ${data.standard_units.toFixed(2)} kWh × ₹${standardRate.toFixed(2)} = ₹${data.standard_cost.toFixed(2)}<br>
                <strong>Off-Peak Hours (10PM-9AM):</strong> ${data.off_peak_units.toFixed(2)} kWh × ₹${offPeakRate.toFixed(2)} = ₹${data.off_peak_cost.toFixed(2)}<br>
                <hr style="margin: 10px 0; border: 1px solid #e5e7eb;">
                <strong style="font-size: 1.1em;">Total Bill: ₹${data.total_cost.toFixed(2)}</strong>
            </div>`;
            
    } catch (error) {
        console.error('Error calculating variable bill:', error);
        document.getElementById('variableBillResult').innerHTML = 
            '<span style="color: #ef4444;">Error calculating bill</span>';
    }
}

// Cleanup intervals when page unloads
window.addEventListener('beforeunload', function() {
    if (applianceDataInterval) clearInterval(applianceDataInterval);
    if (recommendationsInterval) clearInterval(recommendationsInterval);
});