import serial
import requests
import json

ser = serial.Serial("COM5", 115200)

RAILWAY_URL = "https://empty-project-production-899f.up.railway.app/update"

while True:
    try:
        line = ser.readline().decode().strip()

        if not line:
            continue

        data = json.loads(line)

        response = requests.post(
            RAILWAY_URL,
            json=data
        )

        print("Sent:", response.status_code, data)

    except Exception as e:
        print("Error:", e)