"""
PatientPath AI - Detection Tracker
====================================
Standalone YOLOv8 detection tracker that opens a live OpenCV window
with bounding boxes for hospital department video feeds.

Usage:
    python detect.py

Controls:
    1-7 : Switch department camera
    Q / ESC : Quit

Departments:
    1 = Registration    2 = Vision Lab      3 = Dilation Hall
    4 = Diagnostics     5 = Doctor Consult  6 = Pharmacy
    7 = Billing & Insurance
"""

from ultralytics import YOLO
import cv2
import time
import requests
import os

# ---- Configuration ----
MODEL_PATH = "C:/PATIENTPATH-AI/ml_models/yolov8n.pt"
VIDEO_DIR = "C:/PATIENTPATH-AI/frontend/assets/videos"
BACKEND_URL = "http://127.0.0.1:8000"
SEND_INTERVAL = 5  # seconds between backend updates

# Department definitions (press 1-7 to switch)
DEPARTMENTS = [
    {"name": "Registration",        "zone": "registration",      "video": "registration.mp4"},
    {"name": "Vision Lab",          "zone": "vision_lab",        "video": "vision_lab.mp4"},
    {"name": "Dilation Hall",       "zone": "dilation_hall",     "video": "dilation_hall.mp4"},
    {"name": "Diagnostics",         "zone": "diagnostics",       "video": "diagnostics.mp4"},
    {"name": "Doctor Consult",      "zone": "consultation",      "video": "doctor_consult.mp4"},
    {"name": "Pharmacy",            "zone": "pharmacy",          "video": "pharmacy.mp4"},
    {"name": "Billing & Insurance", "zone": "billing_insurance", "video": "billing.mp4"},
]


def open_video(dept_index):
    """Open video capture for the given department index."""
    dept = DEPARTMENTS[dept_index]
    path = os.path.join(VIDEO_DIR, dept["video"])
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"[ERROR] Cannot open video: {path}")
        return None
    return cap


def send_to_backend(zone_name, people_count, confidence):
    """Send detection data to the backend (non-blocking)."""
    payload = {
        "zone_name": zone_name,
        "people_count": people_count,
        "entry_count": 0,
        "exit_count": 0,
        "confidence_score": round(confidence, 3),
        "source": "cv_detection",
    }
    try:
        requests.post(f"{BACKEND_URL}/occupancy/update", json=payload, timeout=2)
    except Exception:
        pass


def main():
    # Load YOLOv8 model
    print("=" * 55)
    print("  PatientPath AI - Detection Tracker")
    print("=" * 55)
    print(f"  Model  : {MODEL_PATH}")
    print(f"  Videos : {VIDEO_DIR}")
    print(f"  Backend: {BACKEND_URL}")
    print("-" * 55)
    print("  Controls:")
    print("    1-7     Switch department camera")
    print("    Q/ESC   Quit")
    print("=" * 55)

    model = YOLO(MODEL_PATH)
    print("[OK] YOLOv8 model loaded\n")

    current_dept = 0
    cap = open_video(current_dept)
    if cap is None:
        print("[ERROR] Failed to open initial video. Exiting.")
        return

    last_send_time = 0
    window_name = "PatientPath AI - Detection Tracker"

    print(f"[LIVE] {DEPARTMENTS[current_dept]['name']}")

    while True:
        ret, frame = cap.read()
        if not ret:
            # Loop video back to start
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = cap.read()
            if not ret:
                print(f"[ERROR] Cannot read frames from {DEPARTMENTS[current_dept]['name']}")
                break

        dept = DEPARTMENTS[current_dept]

        # ---- YOLOv8 Detection (person class only) ----
        results = model(frame, classes=[0], verbose=False)
        boxes = results[0].boxes
        people_count = len(boxes)
        avg_confidence = float(boxes.conf.mean()) if people_count > 0 else 0.0

        # ---- Draw Bounding Boxes (no unique IDs) ----
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])

            # Green bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

            # Confidence label only (no ID)
            label = f"{conf:.0%}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), (0, 255, 0), -1)
            cv2.putText(frame, label, (x1 + 3, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

        # ---- Top Overlay Bar ----
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 50), (0, 0, 0), -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Department name (left)
        cv2.putText(frame, dept["name"], (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2, cv2.LINE_AA)

        # Detected count (right)
        count_text = f"Detected: {people_count}"
        (ctw, _), _ = cv2.getTextSize(count_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        cv2.putText(frame, count_text, (w - ctw - 15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2, cv2.LINE_AA)

        # ---- LIVE indicator (red dot) ----
        cv2.circle(frame, (w - 20, 65), 7, (0, 0, 255), -1)
        cv2.putText(frame, "LIVE", (w - 70, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

        # ---- Bottom info bar ----
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (0, h - 35), (w, h), (0, 0, 0), -1)
        cv2.addWeighted(overlay2, 0.7, frame, 0.3, 0, frame)

        info_text = f"Model: YOLOv8n  |  Confidence: {avg_confidence:.0%}  |  Press 1-7 to switch camera  |  Q to quit"
        cv2.putText(frame, info_text, (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, (200, 200, 200), 1, cv2.LINE_AA)

        # ---- Send to Backend ----
        current_time = time.time()
        if current_time - last_send_time > SEND_INTERVAL:
            send_to_backend(dept["zone"], people_count, avg_confidence)
            last_send_time = current_time

        # ---- Display ----
        cv2.imshow(window_name, frame)

        # ---- Keyboard Controls ----
        key = cv2.waitKey(1) & 0xFF

        if key == 27 or key == ord('q'):
            break

        elif ord('1') <= key <= ord('7'):
            new_dept = key - ord('1')
            if new_dept != current_dept:
                cap.release()
                current_dept = new_dept
                cap = open_video(current_dept)
                if cap is None:
                    print(f"[ERROR] Cannot open {DEPARTMENTS[current_dept]['name']}. Exiting.")
                    break
                print(f"[LIVE] {DEPARTMENTS[current_dept]['name']}")

    if cap is not None:
        cap.release()
    cv2.destroyAllWindows()
    print("\n[STOPPED] Detection tracker closed.")


if __name__ == "__main__":
    main()
