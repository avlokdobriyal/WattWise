import json
import random
from datetime import datetime, timedelta
import math
import os

def generate_realistic_power_data():
    """Generate realistic power consumption data from 1 May to 31 July 2025"""
    data = []
    start_date = datetime(2025, 5, 1, 0, 0, 0)
    end_date = datetime(2025, 7, 31, 23, 59, 59)
    current = start_date

    while current <= end_date:
        hour = current.hour

        base_power = 800 + 400 * math.sin((hour - 6) * math.pi / 12)

        if current.weekday() < 5:  # Weekdays
            base_power *= 1.1

        power = base_power + random.uniform(-100, 150)
        power = max(200, power)

        voltage = random.uniform(220, 240)
        current_amp = power / voltage

        data.append({
            "timestamp": current.isoformat(),
            "voltage": round(voltage, 1),
            "current": round(current_amp, 2),
            "power": round(power, 0)
        })

        current += timedelta(seconds=10)

    return data

def generate_appliance_data(appliance_name, base_power, usage_pattern):
    data = []
    start_date = datetime(2025, 5, 1, 0, 0, 0)
    end_date = datetime(2025, 7, 31, 23, 59, 59)
    current = start_date

    while current <= end_date:
        hour = current.hour
        is_on = False

        if appliance_name == "fridge":
            cycle_factor = math.sin((hour - 14) * math.pi / 12) * 0.3 + 0.7
            is_on = random.random() < cycle_factor * 0.6

        elif appliance_name == "ac":
            if 11 <= hour <= 23:
                is_on = random.random() < 0.8
            else:
                is_on = random.random() < 0.1

        elif appliance_name == "geyser":
            if (6 <= hour <= 9) or (18 <= hour <= 22):
                is_on = random.random() < 0.7
            else:
                is_on = random.random() < 0.05

        elif appliance_name == "microwave":
            if hour in [7, 8, 12, 13, 19, 20, 21]:
                is_on = random.random() < 0.3
            else:
                is_on = random.random() < 0.02

        if is_on:
            power = base_power + random.uniform(-base_power * 0.1, base_power * 0.1)
            voltage = random.uniform(220, 240)
            current_amp = power / voltage
        else:
            power = 0
            voltage = 0
            current_amp = 0

        data.append({
            "timestamp": current.isoformat(),
            "voltage": round(voltage, 1),
            "current": round(current_amp, 2),
            "power": round(power, 0)
        })

        current += timedelta(seconds=10)

    return data

def main():
    print("Generating main power consumption data...")
    main_data = generate_realistic_power_data()
    with open('data/main_power_data.json', 'w') as f:
        json.dump(main_data, f, indent=2)

    appliances = [
        ("fridge", 150, "continuous"),
        ("ac", 1500, "peak_hours"),
        ("geyser", 2000, "morning_evening"),
        ("microwave", 800, "meal_times")
    ]

    for appliance_name, base_power, pattern in appliances:
        print(f"Generating {appliance_name} data...")
        appliance_data = generate_appliance_data(appliance_name, base_power, pattern)
        with open(f'data/{appliance_name}_data.json', 'w') as f:
            json.dump(appliance_data, f, indent=2)

    print("Data generation completed!")
    print("Generated files:")
    print("- data/main_power_data.json")
    print("- data/fridge_data.json")
    print("- data/ac_data.json")
    print("- data/geyser_data.json")
    print("- data/microwave_data.json")

if __name__ == "__main__":
    os.makedirs('data', exist_ok=True)
    main()
