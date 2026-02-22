"""
PatientPath AI - Detection Router
==================================
API endpoints for CV detection status, results, and live video streaming.
"""

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse, JSONResponse
from datetime import datetime

router = APIRouter(prefix="/detection", tags=["Detection"])


@router.get("/status")
async def get_detection_status(request: Request):
    """
    Get the current status of the CV detection service.
    Returns model info, active zones, and latest detection counts.
    """
    cv_service = getattr(request.app.state, "cv_service", None)
    if cv_service is None:
        return {
            "running": False,
            "message": "CV Detection Service not initialized",
            "timestamp": datetime.now().isoformat(),
        }

    status = cv_service.get_status()
    status["timestamp"] = datetime.now().isoformat()
    return status


@router.get("/latest")
async def get_latest_detections(request: Request):
    """
    Get the latest detection results for all zones.
    Returns per-zone people counts and confidence scores.
    """
    cv_service = getattr(request.app.state, "cv_service", None)
    if cv_service is None:
        return {
            "zones": {},
            "timestamp": datetime.now().isoformat(),
        }

    status = cv_service.get_status()
    return {
        "zones": status.get("detections", {}),
        "running": status.get("running", False),
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/stream/{zone_name}")
async def stream_detection(zone_name: str, request: Request):
    """
    Live MJPEG video stream with YOLOv8 bounding box overlays for a department.
    Streams annotated frames continuously at ~12 FPS.
    """
    cv_service = getattr(request.app.state, "cv_service", None)
    if cv_service is None or not cv_service.is_running:
        return JSONResponse(
            status_code=503,
            content={"error": "CV Detection Service not running"}
        )

    valid_zones = [
        "registration", "consultation", "diagnostics",
        "vision_lab", "dilation_hall", "pharmacy", "billing_insurance"
    ]
    if zone_name not in valid_zones:
        return JSONResponse(
            status_code=404,
            content={"error": f"Unknown zone: {zone_name}"}
        )

    return StreamingResponse(
        cv_service.generate_stream(zone_name),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
