import requests
import time
import json

url = "http://127.0.0.1:8000/occupancy/update"
payload = {
    "zone_name": "pharmacy",
    "people_count": 5,
    "unique_ids": [101, 102, 103, 104, 105]
}

print(f"Sending payload: {payload}")
try:
    response = requests.post(url, json=payload)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
