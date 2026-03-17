"""
PatientPath AI — Detection Tracker
====================================
STANDALONE SCRIPT — Run directly (not imported by main.py).

Displays one department at a time with YOLOv8 person detection,
bounding boxes, confidence labels, and live people count.

Usage:
    cd backend
    python detect.py

Controls:
    1-7   Switch department
    Q/ESC Quit

Departments:
    1 = Registration      2 = Vision Lab        3 = Dilation Hall
    4 = Diagnostics       5 = Doctor Consult    6 = Pharmacy
    7 = Billing & Insurance
"""

import sys
import os
import time
import requests

# ── Path setup ────────────────────────────────────────────────────────────────
_BACKEND_DIR  = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
_VIDEO_DIR    = os.path.join(_PROJECT_ROOT, "frontend", "assets", "videos")
_MODEL_PATH   = os.path.join(_PROJECT_ROOT, "ml_models", "yolov8n.pt")
BACKEND_URL   = "http://127.0.0.1:8000"
SEND_INTERVAL = 5  # seconds between backend updates

# ── Dependency check ──────────────────────────────────────────────────────────
try:
    import cv2
    import numpy as np
    from ultralytics import YOLO
except ImportError:
    print("ERROR: Required packages not installed.")
    print("  Run:  pip install opencv-python ultralytics")
    sys.exit(1)

# ── Department definitions — ordered 1 to 7 ───────────────────────────────────
DEPARTMENTS = [
    {"id": 1, "name": "Registration",        "zone": "registration",      "video": "registration.mp4"},
    {"id": 2, "name": "Vision Lab",           "zone": "vision_lab",        "video": "vision_lab.mp4"},
    {"id": 3, "name": "Dilation Hall",        "zone": "dilation_hall",     "video": "dilation_hall.mp4"},
    {"id": 4, "name": "Diagnostics",          "zone": "diagnostics",       "video": "diagnostics.mp4"},
    {"id": 5, "name": "Doctor Consult",       "zone": "consultation",      "video": "doctor_consult.mp4"},
    {"id": 6, "name": "Pharmacy",             "zone": "pharmacy",          "video": "pharmacy.mp4"},
    {"id": 7, "name": "Billing & Insurance",  "zone": "billing_insurance", "video": "billing.mp4"},
]

# ── Detection settings ─────────────────────────────────────────────────────────
PERSON_CLASS_ID = 0      # COCO class 0 = person
MIN_CONFIDENCE  = 0.45   # Minimum confidence threshold

# ── Colors (BGR) ──────────────────────────────────────────────────────────────
C_GREEN  = (0, 255, 0)
C_RED    = (0, 0, 255)
C_WHITE  = (255, 255, 255)
C_BLACK  = (0, 0, 0)
C_GRAY   = (200, 200, 200)


def open_video(dept_index):
    """Open video capture for the given department index."""
    dept = DEPARTMENTS[dept_index]
    path = os.path.join(_VIDEO_DIR, dept["video"])
    if not os.path.isfile(path):
        print(f"  [ERROR] Video not found: {path}")
        return None
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        print(f"  [ERROR] Cannot open video: {path}")
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
    sep = "=" * 58
    print(sep)
    print("  PatientPath AI — Detection Tracker")
    print(sep)
    print(f"  Model  : {os.path.basename(_MODEL_PATH)}")
    print(f"  Videos : {_VIDEO_DIR}")
    print(f"  Backend: {BACKEND_URL}")
    print("-" * 58)
    print("  Controls:")
    print("    1-7     Switch department camera")
    print("    Q/ESC   Quit")
    print("-" * 58)
    print("  Departments:")
    for dept in DEPARTMENTS:
        print(f"    {dept['id']} = {dept['name']}")
    print(sep)

    # 1. Load YOLO model
    if not os.path.isfile(_MODEL_PATH):
        print(f"\nERROR: YOLO model not found:\n  {_MODEL_PATH}")
        sys.exit(1)

    print("\n[INFO] Loading YOLOv8 model ...")
    model = YOLO(_MODEL_PATH)
    print("[OK]   Model loaded.\n")

    # 2. Start with department 1 (Registration)
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

        # ── YOLOv8 Detection (person class only) ──
        results = model(frame, classes=[PERSON_CLASS_ID], verbose=False)
        all_boxes = results[0].boxes
        boxes = [b for b in all_boxes if float(b.conf[0]) >= MIN_CONFIDENCE] if all_boxes is not None else []
        people_count = len(boxes)
        avg_confidence = float(sum(float(b.conf[0]) for b in boxes) / people_count) if people_count > 0 else 0.0

        # ── Draw Bounding Boxes ──
        for box in boxes:
            x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
            conf = float(box.conf[0])

            # Green bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), C_GREEN, 2)

            # Confidence label
            label = f"{conf:.0%}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
            cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), C_GREEN, -1)
            cv2.putText(frame, label, (x1 + 3, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, C_BLACK, 1, cv2.LINE_AA)

        # ── Top Overlay Bar ──
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 50), C_BLACK, -1)
        cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

        # Department name (top-left, red/green)
        cv2.putText(frame, dept["name"], (10, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, C_GREEN, 2, cv2.LINE_AA)

        # Detected count (top-right)
        count_text = f"Detected: {people_count}"
        (ctw, _), _ = cv2.getTextSize(count_text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        cv2.putText(frame, count_text, (w - ctw - 15, 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.9, C_GREEN, 2, cv2.LINE_AA)

        # ── LIVE indicator (red dot + text) ──
        cv2.circle(frame, (w - 20, 65), 7, C_RED, -1)
        cv2.putText(frame, "LIVE", (w - 70, 70),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, C_RED, 1, cv2.LINE_AA)

        # ── Bottom info bar ──
        overlay2 = frame.copy()
        cv2.rectangle(overlay2, (0, h - 35), (w, h), C_BLACK, -1)
        cv2.addWeighted(overlay2, 0.7, frame, 0.3, 0, frame)

        info_text = f"Model: YOLOv8n  |  Confidence: {avg_confidence:.0%}  |  Press 1-7 to switch camera  |  Q to quit"
        cv2.putText(frame, info_text, (10, h - 12),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, C_GRAY, 1, cv2.LINE_AA)

        # ── Send to Backend ──
        current_time = time.time()
        if current_time - last_send_time > SEND_INTERVAL:
            send_to_backend(dept["zone"], people_count, avg_confidence)
            last_send_time = current_time

        # ── Display ──
        cv2.imshow(window_name, frame)

        # ── Keyboard Controls ──
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
