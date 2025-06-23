from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pydantic import BaseModel
import statistics
from optimization_algorithms import PowerOptimizer

app = FastAPI(title="WattWise", description="Smart Electricity Bill Optimizer")
i = 0 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # You can replace * with specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Templates
templates = Jinja2Templates(directory="templates")

# Initialize optimizer
optimizer = PowerOptimizer()

# Load data functions
def load_json_data(filename: str) -> List[Dict]:
    """Load data from JSON file"""
    try:
        with open(f"data/{filename}", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []
    except json.JSONDecodeError:
        return []

def get_filtered_data(data: List[Dict], period: str) -> List[Dict]:
    """Filter data based on time period"""
    if not data:
        return []
    
    now = datetime.now()
    
    if period == "today":
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_time = now - timedelta(days=7)
    elif period == "month":
        start_time = now - timedelta(days=30)
    else:
        return data[-100:]  # Default to last 100 points
    
    filtered_data = []
    for entry in data:
        entry_time = datetime.fromisoformat(entry["timestamp"])
        if entry_time >= start_time:
            filtered_data.append(entry)
    
    # Limit data points for performance
    if len(filtered_data) > 200:
        step = len(filtered_data) // 200
        filtered_data = filtered_data[::step]
    
    return filtered_data

# Pydantic models
class VariableBillingRequest(BaseModel):
    peak_rate: float
    standard_rate: float
    off_peak_rate: float

# Routes
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})

@app.get("/live-data")
async def get_live_data():
    """Get current live power data"""
    try:
        with open("data/iot.json", "r") as f:
            main_data = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        main_data = {}

    return {
        "voltage": main_data.get("voltage", 0),
        "current": main_data.get("current", 0),
        "power": main_data.get("power", 0)
    }


@app.get("/power-data/{period}")
async def get_power_data(period: str):
    """Get power consumption data for charts"""
    main_data = load_json_data("main_power_data.json")
    filtered_data = get_filtered_data(main_data, period)
    return filtered_data

@app.get("/monthly-units")
async def get_monthly_units():
    """Calculate current month's total units"""
    main_data = load_json_data("main_power_data.json")
    if not main_data:
        return {"units": 0}
    
    # Get current month's data
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    monthly_data = []
    for entry in main_data:
        entry_time = datetime.fromisoformat(entry["timestamp"])
        if entry_time >= start_of_month:
            monthly_data.append(entry)
    
    if not monthly_data:
        return {"units": 0}
    
    # Calculate total kWh (power in watts * time in hours)
    total_wh = 0
    for i in range(len(monthly_data) - 1):
        power = monthly_data[i]["power"]
        # Each data point represents 10 seconds = 10/3600 hours
        time_hours = 10 / 3600
        total_wh += power * time_hours
    
    # Convert to kWh
    total_kwh = total_wh / 1000
    
    return {"units": round(total_kwh, 2)}

@app.get("/appliance-data/{appliance}")
async def get_appliance_data(appliance: str):
    """Get current appliance data"""
    valid_appliances = ["fridge", "ac", "geyser", "microwave"]
    if appliance not in valid_appliances:
        raise HTTPException(status_code=404, detail="Appliance not found")
    
    appliance_data = load_json_data(f"{appliance}_data.json")
    if not appliance_data:
        return {"voltage": 0, "current": 0, "power": 0}
    global i
    # Return the latest data point
    latest = appliance_data[i]
    i=i+1
    return {
        "voltage": latest["voltage"],
        "current": latest["current"],
        "power": latest["power"]
    }


@app.get("/slot-recommendations")
async def get_slot_recommendations():
    """Get time slot recommendations using greedy algorithm"""
    main_data = load_json_data("main_power_data.json")
    recommendations = optimizer.greedy_slot_recommendation(main_data)
    return {"recommendations": recommendations}

@app.get("/peak-detection")
async def get_peak_detection():
    """Get peak detection results using sliding window"""
    main_data = load_json_data("main_power_data.json")
    peaks = optimizer.sliding_window_peak_detection(main_data)
    return {"peaks": peaks}

@app.get("/live-recommendations")
async def get_live_recommendations():
    """Get live optimization recommendations"""
    main_data = load_json_data("main_power_data.json")
    
    # Get appliance data
    appliance_data = {}
    for appliance in ["fridge", "ac", "geyser", "microwave"]:
        appliance_data[appliance] = load_json_data(f"{appliance}_data.json")
    
    recommendations = optimizer.generate_live_recommendations(main_data, appliance_data)
    return {"recommendations": recommendations}

@app.post("/variable-billing")
async def calculate_variable_billing(billing_request: VariableBillingRequest):
    """Calculate variable rate electricity bill"""
    # Get monthly units data
    monthly_units_response = await get_monthly_units()
    total_units = monthly_units_response["units"]
    
    if total_units == 0:
        return {
            "peak_units": 0,
            "standard_units": 0,
            "off_peak_units": 0,
            "peak_cost": 0,
            "standard_cost": 0,
            "off_peak_cost": 0,
            "total_cost": 0
        }
    
    # Load main data to analyze time-based consumption
    main_data = load_json_data("main_power_data.json")
    now = datetime.now()
    start_of_month = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Filter monthly data
    monthly_data = []
    for entry in main_data:
        entry_time = datetime.fromisoformat(entry["timestamp"])
        if entry_time >= start_of_month:
            monthly_data.append(entry)
    
    if not monthly_data:
        return {
            "peak_units": 0,
            "standard_units": 0,
            "off_peak_units": 0,
            "peak_cost": 0,
            "standard_cost": 0,
            "off_peak_cost": 0,
            "total_cost": 0
        }
    
    # Calculate time-slot based consumption
    peak_consumption = 0  # 9 AM - 6 PM
    standard_consumption = 0  # 6 PM - 10 PM
    off_peak_consumption = 0  # 10 PM - 9 AM
    
    for i in range(len(monthly_data) - 1):
        entry_time = datetime.fromisoformat(monthly_data[i]["timestamp"])
        hour = entry_time.hour
        power = monthly_data[i]["power"]
        
        # Each data point represents 10 seconds = 10/3600 hours
        time_hours = 10 / 3600
        consumption_wh = power * time_hours
        
        if 9 <= hour < 18:  # Peak hours
            peak_consumption += consumption_wh
        elif 18 <= hour < 22:  # Standard hours
            standard_consumption += consumption_wh
        else:  # Off-peak hours
            off_peak_consumption += consumption_wh
    
    # Convert to kWh
    peak_units = peak_consumption / 1000
    standard_units = standard_consumption / 1000
    off_peak_units = off_peak_consumption / 1000
    
    # Calculate costs
    peak_cost = peak_units * billing_request.peak_rate
    standard_cost = standard_units * billing_request.standard_rate
    off_peak_cost = off_peak_units * billing_request.off_peak_rate
    total_cost = peak_cost + standard_cost + off_peak_cost
    
    return {
        "peak_units": round(peak_units, 2),
        "standard_units": round(standard_units, 2),
        "off_peak_units": round(off_peak_units, 2),
        "peak_cost": round(peak_cost, 2),
        "standard_cost": round(standard_cost, 2),
        "off_peak_cost": round(off_peak_cost, 2),
        "total_cost": round(total_cost, 2)
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)