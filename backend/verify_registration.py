
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def verify_registration():
    tracking_id = f"TEST-REG-{int(time.time())}"
    
    payload = {
        "department": "registration",
        "action": "New Patient Registration",
        "tracking_id": tracking_id,
        "name": "Test Verification User",
        "mobile": "9988776655",
        "next_department": "vision_lab"
    }
    
    print(f"1. Registering new patient: {tracking_id}")
    try:
        response = requests.post(f"{BASE_URL}/patient/update-stage", json=payload)
        if response.status_code == 200:
            print("   Registration Success:", response.json())
        else:
            print(f"   Registration Failed: {response.status_code} - {response.text}")
            return

        print(f"2. Verifying patient data...")
        response = requests.get(f"{BASE_URL}/patient/tracking/{tracking_id}")
        if response.status_code == 200:
            data = response.json()
            print("   Patient Data Retrieved:")
            print(f"   Name: {data.get('name')}")
            print(f"   Mobile: {data.get('mobile')}")
            print(f"   Zone: {data.get('current_zone')}")
            
            if data.get('name') == payload['name'] and data.get('mobile') == payload['mobile']:
                print("   SUCCESS: Data matches!")
            else:
                print("   FAILURE: Data mismatch!")
        else:
            print(f"   Verification Failed: {response.status_code} - {response.text}")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    verify_registration()
