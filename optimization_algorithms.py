import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import statistics

class PowerOptimizer:
    """Class containing optimization algorithms for power consumption"""
    
    def __init__(self, threshold_watts: int = 1200):
     self.peak_threshold_multiplier = 1.05
     self.window_size = 12
     self.threshold_watts = 850

    
    def greedy_slot_recommendation(self, power_data: List[Dict], rate_structure: Dict = None) -> List[Dict]:
        """
        Greedy algorithm for optimal time slot recommendations
        Finds the cheapest time slots for high-power activities
        """
        if not power_data:
            return []
        
        # Default rate structure (variable pricing)
        if not rate_structure:
            rate_structure = {
                "peak": {"hours": range(9, 18), "rate": 8.0},      # 9 AM - 6 PM
                "standard": {"hours": range(18, 22), "rate": 6.0}, # 6 PM - 10 PM
                "off_peak": {"hours": list(range(0, 9)) + list(range(22, 24)), "rate": 4.0}  # 10 PM - 9 AM
            }
        
        # Analyze hourly average consumption and costs
        hourly_data = {}
        for entry in power_data[-8640:]:  # Last 30 days
            dt = datetime.fromisoformat(entry["timestamp"])
            hour = dt.hour
            
            if hour not in hourly_data:
                hourly_data[hour] = {"powers": [], "rate": 0}
            
            hourly_data[hour]["powers"].append(entry["power"])
            
            # Determine rate for this hour
            if hour in rate_structure["peak"]["hours"]:
                hourly_data[hour]["rate"] = rate_structure["peak"]["rate"]
            elif hour in rate_structure["standard"]["hours"]:
                hourly_data[hour]["rate"] = rate_structure["standard"]["rate"]
            else:
                hourly_data[hour]["rate"] = rate_structure["off_peak"]["rate"]
        
        # Calculate average power and cost per hour
        hourly_analysis = []
        for hour, data in hourly_data.items():
            avg_power = statistics.mean(data["powers"])
            cost_per_kwh = data["rate"]
            cost_efficiency = avg_power * cost_per_kwh  # Lower is better
            
            hourly_analysis.append({
                "hour": hour,
                "avg_power": avg_power,
                "rate": cost_per_kwh,
                "cost_efficiency": cost_efficiency
            })
        
        # Sort by cost efficiency (greedy approach - cheapest first)
        hourly_analysis.sort(key=lambda x: x["cost_efficiency"])
        
        recommendations = []
        
        # Recommend best off-peak hours
        off_peak_hours = [h for h in hourly_analysis if h["rate"] == rate_structure["off_peak"]["rate"]][:3]
        if off_peak_hours:
            best_off_peak = min(off_peak_hours, key=lambda x: x["cost_efficiency"])
            recommendations.append({
                "time_slot": f"{best_off_peak['hour']:02d}:00 - {(best_off_peak['hour']+1)%24:02d}:00",
                "recommendation": "Optimal time for high-power appliances (washing machine, dishwasher)",
                "savings": round((rate_structure["peak"]["rate"] - best_off_peak["rate"]) * 2.0, 2),  # Assuming 2 kWh appliance
                "reason": "Lowest electricity rate with minimal grid load"
            })
        
        # Recommend avoiding peak hours
        peak_hours = [h for h in hourly_analysis if h["rate"] == rate_structure["peak"]["rate"]]
        if peak_hours:
            worst_peak = max(peak_hours, key=lambda x: x["cost_efficiency"])
            recommendations.append({
                "time_slot": f"{worst_peak['hour']:02d}:00 - {(worst_peak['hour']+1)%24:02d}:00",
                "recommendation": "Avoid using high-power appliances during this time",
                "savings": round((worst_peak["rate"] - rate_structure["off_peak"]["rate"]) * 2.0, 2),
                "reason": "Highest electricity rate and peak consumption period"
            })
        
        # General optimization recommendation
        if len(hourly_analysis) >= 3:
            recommendations.append({
                "time_slot": "General Optimization",
                "recommendation": "Shift 30% of discretionary power usage to off-peak hours",
                "savings": round(statistics.mean([r.get("savings", 0) for r in recommendations]) * 1.5, 2),
                "reason": "Load balancing across time slots"
            })
        
        return recommendations
    
    def sliding_window_peak_detection(self, power_data: List[Dict]) -> List[Dict]:
     """
     Sliding window algorithm for detecting power consumption peaks
     Identifies abnormal power spikes that could indicate inefficient usage
     """
     if len(power_data) < self.window_size:
         print("[DEBUG] Not enough data for peak detection.")
         return []

     peaks = []
     recent_data = power_data[-1440:]  # Last 24 hours

     for i in range(len(recent_data) - self.window_size):
         window = recent_data[i:i + self.window_size]
         window_powers = [entry["power"] for entry in window if "power" in entry]

         if not window_powers or len(window_powers) < self.window_size:
             continue

         avg_power = statistics.mean(window_powers)
         current_entry = recent_data[i + self.window_size]
         current_power = current_entry.get("power", 0)

         print(f"[DEBUG] i={i}, avg={avg_power:.2f}, current={current_power:.2f}")

         if (
             current_power > avg_power * self.peak_threshold_multiplier
            or current_power > self.threshold_watts
         ):
             timestamp = current_entry.get("timestamp")
             if not timestamp:
                 continue

             try:
                 peak_time = datetime.fromisoformat(timestamp)
             except ValueError:
                 continue

             suggestion = self._get_peak_suggestion(current_power, peak_time.hour)

             peaks.append({
                 "timestamp": timestamp,
                 "power": current_power,
                 "average_power": round(avg_power, 1),
                 "peak_ratio": round(current_power / avg_power, 2),
                 "suggestion": suggestion
             })
             print(f"[PEAK] {timestamp} | {current_power:.2f}W")

     # Remove duplicates within 5 minutes
     filtered_peaks = []
     for peak in peaks:
         peak_time = datetime.fromisoformat(peak["timestamp"])
         is_duplicate = False
         for existing_peak in filtered_peaks:
             existing_time = datetime.fromisoformat(existing_peak["timestamp"])
             if abs((peak_time - existing_time).total_seconds()) < 300:
                 is_duplicate = True
                 break
         if not is_duplicate:
             filtered_peaks.append(peak)

     # Sort by significance
     filtered_peaks.sort(key=lambda x: x["peak_ratio"], reverse=True)
     print(f"[DEBUG] Total peaks detected: {len(filtered_peaks)}")
     return filtered_peaks[:5]

    
    def _get_peak_suggestion(self, power: float, hour: int) -> str:
        """Generate contextual suggestions based on power level and time"""
        if power > 2500:
            if 6 <= hour <= 10:
                return "High power usage detected in morning hours. Consider staggering water heater and other appliances."
            elif 18 <= hour <= 22:
                return "Evening peak detected. Try to avoid simultaneous use of AC, water heater, and kitchen appliances."
            else:
                return "Unusual high power consumption. Check for appliances left on unnecessarily."
        elif power > 1800:
            return "Moderate peak detected. Consider load balancing by turning off non-essential appliances."
        else:
            return "Minor peak detected. Monitor appliance usage patterns for optimization opportunities."
    
    def generate_live_recommendations(self, main_data: List[Dict], appliance_data: Dict[str, List[Dict]]) -> List[Dict]:
        """Generate live optimization recommendations based on current usage patterns"""
        if not main_data:
            return []
        
        recommendations = []
        
        # Get recent data (last hour)
        recent_main = main_data[-360:] if len(main_data) >= 360 else main_data  # Last hour
        current_power = recent_main[-1]["power"] if recent_main else 0
        avg_recent_power = statistics.mean([d["power"] for d in recent_main]) if recent_main else 0
        
        current_time = datetime.now()
        hour = current_time.hour
        
        # Analyze appliance usage
        active_appliances = []
        total_appliance_power = 0
        
        for appliance_name, data in appliance_data.items():
            if data:
                recent_appliance_power = data[-1]["power"]
                if recent_appliance_power > 10:  # Consider appliance active if > 10W
                    active_appliances.append({
                        "name": appliance_name,
                        "power": recent_appliance_power
                    })
                    total_appliance_power += recent_appliance_power
        
        # Time-based recommendations
        if 9 <= hour <= 18:  # Peak hours
            if current_power > 1500:
                recommendations.append({
                    "title": "Peak Hour High Usage Alert",
                    "description": f"Currently using {current_power}W during peak rate hours. Consider postponing non-essential appliances.",
                    "savings": round((current_power - 800) * 0.004, 2)  # 4 paise per watt-hour saved
                })
        
        elif 22 <= hour or hour <= 6:  # Off-peak hours
            if len(active_appliances) < 2:
                recommendations.append({
                    "title": "Off-Peak Opportunity",
                    "description": "This is an optimal time to run dishwashers, washing machines, or charge electric vehicles.",
                    "savings": 2.50
                })
        
        # Appliance-specific recommendations
        ac_data = next((app for app in active_appliances if app["name"] == "ac"), None)
        if ac_data and ac_data["power"] > 1200:
            recommendations.append({
                "title": "AC Optimization",
                "description": "AC is consuming high power. Consider increasing temperature by 1-2°C or using timer mode.",
                "savings": round(ac_data["power"] * 0.002, 2)
            })
        
        geyser_data = next((app for app in active_appliances if app["name"] == "geyser"), None)
        if geyser_data and geyser_data["power"] > 1800:
            if not (6 <= hour <= 9 or 18 <= hour <= 22):
                recommendations.append({
                    "title": "Water Heater Alert",
                    "description": "Water heater is running outside typical usage hours. Consider using a timer.",
                    "savings": 1.75
                })
        
        # General efficiency recommendations
        if current_power > avg_recent_power * 1.4:
            recommendations.append({
                "title": "Unusual Power Spike",
                "description": f"Power usage is {round((current_power/avg_recent_power - 1) * 100)}% higher than recent average. Check for appliances that may have been left on.",
                "savings": round((current_power - avg_recent_power) * 0.003, 2)
            })
        
        # If no specific recommendations, provide general tip
        if not recommendations:
            tips = [
                {
                    "title": "Efficient Usage Detected",
                    "description": "Your current power consumption is optimal. Maintain this pattern for maximum savings.",
                    "savings": 0
                },
                {
                    "title": "Smart Monitoring Active",
                    "description": "WattWise is continuously monitoring your usage patterns for optimization opportunities.",
                    "savings": 0
                }
            ]
            recommendations.append(tips[hash(str(hour)) % len(tips)])
        
        return recommendations[:3]  # Return top 3 recommendations

# Example usage and testing functions
def test_algorithms():
    """Test the optimization algorithms with sample data"""
    optimizer = PowerOptimizer()
    
    # Generate sample data for testing
    sample_data = []
    base_time = datetime.now() - timedelta(hours=24)
    
    for i in range(1440):  # 24 hours of data
        timestamp = base_time + timedelta(minutes=i * 1)  # Every minute
        power = 800 + 200 * (i % 100) / 100  # Varying power
        sample_data.append({
            "timestamp": timestamp.isoformat(),
            "power": power,
            "voltage": 230,
            "current": power / 230
        })
    
    # Test greedy algorithm
    print("Testing Greedy Slot Recommendations:")
    slot_recs = optimizer.greedy_slot_recommendation(sample_data)
    for rec in slot_recs:
        print(f"- {rec['time_slot']}: {rec['recommendation']}")
    
    # Test sliding window peak detection
    print("\nTesting Peak Detection:")
    peaks = optimizer.sliding_window_peak_detection(sample_data)
    for peak in peaks:
        print(f"- Peak at {peak['timestamp']}: {peak['power']}W")

if __name__ == "__main__":
    test_algorithms()
