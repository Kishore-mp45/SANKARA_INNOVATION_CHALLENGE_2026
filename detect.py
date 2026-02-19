from ultralytics import YOLO
import cv2
import time
import requests

# Load YOLO model
model = YOLO("C:/PATIENTPATH-AI/yolov8n.pt")

# Video Source
cap = cv2.VideoCapture("C:/PATIENTPATH-AI/hospital_video.mp4")

# Person State Store
person_state = {}

last_send_time = 0

import numpy as np

# Color Definitions for Staff (HSV)
# White Coat: Low saturation, high value
LOWER_WHITE = np.array([0, 0, 200])
UPPER_WHITE = np.array([180, 30, 255])

# Blue Scrubs: Blue hue
LOWER_BLUE = np.array([100, 150, 0])
UPPER_BLUE = np.array([140, 255, 255])

def is_patient(frame, box):
    x1, y1, x2, y2 = map(int, box)
    # Ensure crops are within frame
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
    
    crop = frame[y1:y2, x1:x2]
    if crop.size == 0: return True # Default to patient if crop fails

    # Convert to HSV
    hsv_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)

    # Check for Staff Colors
    mask_white = cv2.inRange(hsv_crop, LOWER_WHITE, UPPER_WHITE)
    mask_blue = cv2.inRange(hsv_crop, LOWER_BLUE, UPPER_BLUE)
    
    # Calculate percentage of pixels matching staff colors
    white_ratio = np.sum(mask_white > 0) / crop.size
    blue_ratio = np.sum(mask_blue > 0) / crop.size
    
    # If dominant color is white or blue, likely staff
    if white_ratio > 0.15 or blue_ratio > 0.15:
        return False # Is Staff
        
    return True # Is Patient

while True:
    ret, frame = cap.read()
    if not ret:
        cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
        continue

    # YOLO + ByteTrack
    results = model.track(
        frame,
        persist=True,
        tracker="bytetrack.yaml",
        classes=[0]   # Only person class
    )

    current_time = time.time()

    if results[0].boxes.id is not None:
        ids = results[0].boxes.id.cpu().numpy().astype(int)
        boxes = results[0].boxes.xyxy.cpu().numpy()

        for person_id, box in zip(ids, boxes):
            x1, y1, x2, y2 = map(int, box)
            person_id = int(person_id) # Convert to standard int

            # Update Person State
            if person_id not in person_state:
                # Classify on first sight
                role = "patient" if is_patient(frame, box) else "staff"
                person_state[person_id] = {
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "role": role,
                    "zones": set()
                }
            else:
                person_state[person_id]["last_seen"] = current_time

            # Use role from state (consistency)
            role = person_state[person_id]["role"]
            color = (0, 255, 0) if role == "patient" else (0, 0, 255) # Green for Patient, Red for Staff

            # Draw Box + ID
            cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
            cv2.putText(frame, f"ID {person_id} ({role})", (x1, y1-10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

    # People Count - Current Frame Only (Patients Only)
    current_patient_ids = [pid for pid, data in person_state.items() 
                           if (current_time - data["last_seen"] < 0.5) and (data["role"] == "patient")]
    
    current_staff_ids = [pid for pid, data in person_state.items() 
                           if (current_time - data["last_seen"] < 0.5) and (data["role"] == "staff")]

    people_count = len(current_patient_ids)

    # Display Count
    cv2.putText(frame, f"Patients: {people_count}", (20,40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,255,0), 2)
    cv2.putText(frame, f"Staff: {len(current_staff_ids)}", (20,80), cv2.FONT_HERSHEY_SIMPLEX, 1, (0,0,255), 2)

    # Send Data to Backend Every 2 Seconds
    if current_time - last_send_time > 2:
        payload = {
            "zone_name": "pharmacy", 
            "people_count": people_count, 
            "timestamp": time.strftime("%H:%M:%S"), 
            "unique_ids": current_patient_ids 
        }

        try:
            requests.post("http://127.0.0.1:8000/occupancy/update", json=payload)
        except Exception as e:
            print(f"Failed to send data: {e}")

        last_send_time = current_time

    cv2.imshow("Tracking", frame)

    key = cv2.waitKey(1) & 0xFF
    if key == 27 or key == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()
