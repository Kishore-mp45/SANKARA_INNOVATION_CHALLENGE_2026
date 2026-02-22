import cv2
import time
import requests
import json
from ultralytics import YOLO

# Initialize YOLO model (using larger model for better accuracy)
model = YOLO('ml_models/yolov8n.pt')  # Can upgrade to yolov8m.pt or yolov8l.pt

# Video source (0 for webcam, or path to video file)
video_source = 0  # Changed to 0 for webcam testing, or use specific file if available
# video_source = "path/to/video.mp4" 

# Check if webcam is available, otherwise mock it (for headless server without cam)
cap = cv2.VideoCapture(video_source, cv2.CAP_DSHOW) # standard capture
if not cap.isOpened():
    print("Webcam not found, checking for video files...")
    # fallback or exit
    # For this verification task, we might not have a camera. 
    # But YOLO needs an image.
    pass

# Backend API endpoint
API_URL = "http://127.0.0.1:8000/occupancy/update"

# Zone configuration
ZONE_NAME = "pharmacy" # Must match seed data

def process_frame(frame, frame_count):
    # Run tracking
    results = model.track(frame, persist=True, verbose=False, classes=[0]) # class 0 is person
    
    # Process results
    current_ids = set()
    
    if results and results[0].boxes and results[0].boxes.id is not None:
        boxes = results[0].boxes.xywh.cpu().numpy()
        track_ids = results[0].boxes.id.int().cpu().tolist()
        
        for track_id in track_ids:
            current_ids.add(track_id)
            
    # Count people
    people_count = len(current_ids)
    
    # Prepare payload
    payload = {
        "zone_name": ZONE_NAME,
        "people_count": people_count,
        "entry_count": 0, # Placeholder
        "exit_count": 0, # Placeholder
        "confidence_score": 0.95, # Mock confidence
        "source": "cv_detection",
        "unique_ids": list(current_ids)
    }
    
    # Send to backend (every 30 frames to avoid spamming)
    if frame_count % 30 == 0:
        try:
            response = requests.post(API_URL, json=payload)
            if response.status_code == 200:
                print(f"Frame {frame_count}: Successfully sent data. Count: {people_count}, IDs: {list(current_ids)}")
                print(f"Response: {response.json()}")
            else:
                print(f"Frame {frame_count}: Failed to send data. Status: {response.status_code}")
                print(f"Error: {response.text}")
        except Exception as e:
            print(f"Frame {frame_count}: Connection error: {e}")

def main():
    print(f"Starting headless detection for zone: {ZONE_NAME}")
    
    if not cap.isOpened():
        print("No video source. Creating mock frames.")
        import numpy as np
        # Create black frame
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        
        for i in range(100): # Run 100 iterations
            process_frame(frame, i)
            time.sleep(0.1)
    else:
        frame_count = 0
        max_frames = 100 # Run for short time
        
        while frame_count < max_frames:
            success, frame = cap.read()
            if not success:
                break
                
            process_frame(frame, frame_count)
            frame_count += 1
            # time.sleep(0.01) # Simulate real time
        
        cap.release()

    print("Headless detection verification complete.")

if __name__ == "__main__":
    main()
