"""
PatientPath AI - CV Detection Service
======================================
Background service that uses YOLOv8 to detect and count people
in department video feeds, updating zone occupancy in real-time.
Provides MJPEG streaming with bounding box overlays.
"""

import threading
import time
import asyncio
import os
import logging
from datetime import datetime
from typing import Dict, Optional

import cv2
import numpy as np
from ultralytics import YOLO

logger = logging.getLogger(__name__)

# Zone name -> video filename mapping
ZONE_VIDEO_MAP = {
    "registration": "registration.mp4",
    "consultation": "consultation.mp4",
    "diagnostics": "diagnostics.mp4",
    "vision_lab": "vision.mp4",
    "dilation_hall": "dilation.mp4",
    "pharmacy": "pharmacy.mp4",
    "billing_insurance": "billing.mp4",
}

ZONE_DISPLAY_NAMES = {
    "registration": "Registration",
    "consultation": "Consultation",
    "diagnostics": "Diagnostics",
    "vision_lab": "Vision Lab",
    "dilation_hall": "Dilation Hall",
    "pharmacy": "Pharmacy",
    "billing_insurance": "Billing & Insurance",
}

PERSON_CLASS_ID = 0  # COCO class 0 = person


class CVDetectionService:
    """
    Background service that continuously processes department video feeds
    using YOLOv8 to count people and update zone occupancy.
    Also provides MJPEG streaming with bounding box overlays.
    """

    def __init__(self, model_path: str, video_dir: str, event_loop: asyncio.AbstractEventLoop):
        self.model_path = model_path
        self.video_dir = video_dir
        self.event_loop = event_loop
        self.model: Optional[YOLO] = None
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._captures: Dict[str, cv2.VideoCapture] = {}
        self._latest: Dict[str, dict] = {}
        self._lock = threading.Lock()
        self._model_lock = threading.Lock()
        self._interval = 5  # seconds between detection cycles

    def start(self):
        """Load model and start the detection background thread."""
        logger.info("Loading YOLOv8 model from %s", self.model_path)
        self.model = YOLO(self.model_path)
        logger.info("YOLOv8 model loaded successfully")

        # Open video captures for each zone
        for zone_name, video_file in ZONE_VIDEO_MAP.items():
            video_path = os.path.join(self.video_dir, video_file)
            if os.path.isfile(video_path):
                cap = cv2.VideoCapture(video_path)
                if cap.isOpened():
                    self._captures[zone_name] = cap
                    logger.info("Opened video feed: %s -> %s", zone_name, video_file)
                else:
                    logger.warning("Could not open video: %s", video_path)
            else:
                logger.warning("Video file not found: %s", video_path)

        if not self._captures:
            logger.error("No video feeds available. CV detection will not run.")
            return

        self._running = True
        self._thread = threading.Thread(target=self._detection_loop, daemon=True, name="cv-detection")
        self._thread.start()
        logger.info("CV Detection Service started (%d zones, %ds interval)", len(self._captures), self._interval)

    def stop(self):
        """Stop the detection thread and release video captures."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=10)
        for cap in self._captures.values():
            cap.release()
        self._captures.clear()
        logger.info("CV Detection Service stopped")

    @property
    def is_running(self) -> bool:
        return self._running and self._thread is not None and self._thread.is_alive()

    def get_status(self) -> dict:
        """Return current detection status for all zones."""
        with self._lock:
            return {
                "running": self.is_running,
                "model": os.path.basename(self.model_path),
                "zones_active": len(self._captures),
                "interval_seconds": self._interval,
                "detections": dict(self._latest),
            }

    def get_latest_counts(self) -> Dict[str, int]:
        """Return latest people count per zone."""
        with self._lock:
            return {zone: data["count"] for zone, data in self._latest.items()}

    def generate_stream(self, zone_name: str):
        """
        Generator that yields MJPEG frames with YOLOv8 bounding box overlays.
        Opens a dedicated VideoCapture for the stream, runs inference per frame,
        and draws detection boxes continuously.
        """
        video_file = ZONE_VIDEO_MAP.get(zone_name)
        if not video_file:
            logger.warning("Stream requested for unknown zone: %s", zone_name)
            return

        video_path = os.path.join(self.video_dir, video_file)
        if not os.path.isfile(video_path):
            logger.warning("Video not found for stream: %s", video_path)
            return

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            logger.warning("Cannot open video for stream: %s", video_path)
            return

        zone_display = ZONE_DISPLAY_NAMES.get(zone_name, zone_name)
        logger.info("Stream started for zone: %s", zone_name)

        try:
            while self._running:
                ret, frame = cap.read()
                if not ret:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    if not ret:
                        break

                # Run YOLOv8 inference with model lock for thread safety
                people_count = 0
                try:
                    with self._model_lock:
                        results = self.model(frame, classes=[PERSON_CLASS_ID], verbose=False)
                    boxes = results[0].boxes
                    people_count = len(boxes)

                    # Draw bounding boxes (green, no unique IDs)
                    for box in boxes:
                        x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                        conf = float(box.conf[0])

                        # Green bounding box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)

                        # Confidence label (no ID)
                        label = f"{conf:.0%}"
                        (tw, th), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                        cv2.rectangle(frame, (x1, y1 - th - 8), (x1 + tw + 6, y1), (0, 255, 0), -1)
                        cv2.putText(frame, label, (x1 + 3, y1 - 5),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1, cv2.LINE_AA)

                except Exception as e:
                    logger.error("Stream inference error for %s: %s", zone_name, e)

                # Top overlay bar - zone name + count
                h, w = frame.shape[:2]
                overlay = frame.copy()
                cv2.rectangle(overlay, (0, 0), (w, 40), (0, 0, 0), -1)
                cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

                cv2.putText(frame, f"{zone_display}", (10, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

                count_text = f"Detected: {people_count}"
                (ctw, _), _ = cv2.getTextSize(count_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
                cv2.putText(frame, count_text, (w - ctw - 10, 28),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)

                # LIVE indicator
                cv2.circle(frame, (w - 15, 55), 6, (0, 0, 255), -1)
                cv2.putText(frame, "LIVE", (w - 60, 60),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1, cv2.LINE_AA)

                # Encode frame to JPEG
                _, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

                time.sleep(1 / 12)  # ~12 FPS

        except GeneratorExit:
            logger.info("Stream client disconnected for zone: %s", zone_name)
        finally:
            cap.release()
            logger.info("Stream ended for zone: %s", zone_name)

    # ---- internal ----

    def _detection_loop(self):
        """Main detection loop running in a background thread."""
        logger.info("CV detection loop started")

        while self._running:
            cycle_start = time.time()

            for zone_name, cap in list(self._captures.items()):
                if not self._running:
                    break

                ret, frame = cap.read()
                if not ret:
                    # Video ended, loop back to start
                    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    ret, frame = cap.read()
                    if not ret:
                        logger.warning("Cannot read frames from %s", zone_name)
                        continue

                try:
                    # Run YOLOv8 inference with model lock
                    with self._model_lock:
                        results = self.model(frame, classes=[PERSON_CLASS_ID], verbose=False)
                    boxes = results[0].boxes

                    people_count = len(boxes)
                    avg_confidence = float(boxes.conf.mean()) if people_count > 0 else 0.0

                    # Store latest result
                    with self._lock:
                        self._latest[zone_name] = {
                            "count": people_count,
                            "confidence": round(avg_confidence, 3),
                            "timestamp": datetime.now().isoformat(),
                        }

                    # Update database
                    self._update_zone_occupancy(zone_name, people_count, avg_confidence)

                    # Broadcast via WebSocket
                    self._schedule_broadcast(zone_name, people_count)

                except Exception as e:
                    logger.error("Detection error for %s: %s", zone_name, e)

            # Wait for the rest of the interval
            elapsed = time.time() - cycle_start
            sleep_time = max(0, self._interval - elapsed)
            if sleep_time > 0 and self._running:
                time.sleep(sleep_time)

        logger.info("CV detection loop ended")

    def _update_zone_occupancy(self, zone_name: str, people_count: int, confidence: float):
        """Update Zone.current_occupancy and create an OccupancyLog entry."""
        try:
            from database.database import get_db_context
            from models.zone import Zone
            from models.occupancy import OccupancyLog

            with get_db_context() as db:
                zone = db.query(Zone).filter(Zone.zone_name == zone_name).first()
                previous_count = zone.current_occupancy if zone else 0

                if zone:
                    zone.current_occupancy = people_count
                    zone.updated_at = datetime.now()

                # Create occupancy log entry
                log = OccupancyLog(
                    zone_name=zone_name,
                    people_count=people_count,
                    previous_count=previous_count,
                    entry_count=max(0, people_count - previous_count),
                    exit_count=max(0, previous_count - people_count),
                    confidence_score=confidence,
                    source="cv_detection",
                    timestamp=datetime.now(),
                )
                db.add(log)
                db.commit()

        except Exception as e:
            logger.error("DB update error for %s: %s", zone_name, e)

    def _schedule_broadcast(self, zone_name: str, people_count: int):
        """Schedule a WebSocket broadcast on the main event loop."""
        try:
            from routers.websocket import broadcast_occupancy_update

            asyncio.run_coroutine_threadsafe(
                broadcast_occupancy_update({
                    "zone": zone_name,
                    "count": people_count,
                    "timestamp": datetime.now().isoformat(),
                }),
                self.event_loop,
            )
        except Exception as e:
            logger.error("Broadcast error for %s: %s", zone_name, e)
