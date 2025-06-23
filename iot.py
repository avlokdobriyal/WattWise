import serial
import json
import os

PORT = 'COM4'  # Change this to your actual COM port
BAUD = 115200
OUTPUT_PATH = r"C:\Users\avlok\AppData\Local\Programs\WattWise\data\iot.json"

ser = serial.Serial(PORT, BAUD, timeout=2)
print(f"Listening on {PORT}...")

buffer = []
recording = False

while True:
    try:
        line = ser.readline().decode('utf-8', errors='ignore').strip()

        if '{' in line:
            recording = True
            buffer = [line]
        elif '}' in line and recording:
            buffer.append(line)
            full_json_str = '\n'.join(buffer)
            try:
                data = json.loads(full_json_str)
                os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
                with open(OUTPUT_PATH, 'w') as f:
                    json.dump(data, f, indent=2)
                print("iot.json updated:", data)
            except json.JSONDecodeError as e:
                print("Failed to parse JSON:", e)
            recording = False
            buffer = []
        elif recording:
            buffer.append(line)
        else:
            print("Non-JSON line skipped:", line)

    except KeyboardInterrupt:
        print("Stopped by user.")
        break
    except Exception as e:
        print("Error:", e)
