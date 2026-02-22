import requests
import sys

url = "http://localhost:8000/prediction/average-wait"

try:
    response = requests.get(url)
    print(f"Status Code: {response.status_code}")
    if response.status_code == 200:
        print("Response JSON:")
        print(response.json())
        sys.exit(0)
    else:
        print(f"Error Response: {response.text}")
        sys.exit(1)
except Exception as e:
    print(f"Request failed: {e}")
    sys.exit(1)
