"""Hospital Load Status Router - Real-time department load for patients."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.prediction_service import PredictionService
from models.zone import Zone

router = APIRouter(prefix="/hospital", tags=["Hospital"])


def _classify_load(queue_size: int, capacity: int) -> dict:
    """
    Classify department load level using capacity percentages to match Live Occupancy.
    
    LOW (Green):     <= 40%
    MEDIUM (Yellow): <= 75%
    HIGH (Red):      > 75%
    """
    if capacity <= 0:
        pct = 0
    else:
        pct = (queue_size / capacity) * 100

    if pct <= 40:
        return {"load_level": "LOW", "icon": "\U0001f7e2", "label": "Low Load"}
    elif pct <= 75:
        return {"load_level": "MEDIUM", "icon": "\U0001f7e1", "label": "Medium Load"}
    else:
        return {"load_level": "HIGH", "icon": "\U0001f534", "label": "High Load"}


# Display names matching user requirements
DEPARTMENT_DISPLAY_NAMES = {
    "registration": "Registration",
    "vision_lab": "Vision Lab",
    "dilation_hall": "Dilation",
    "consultation": "Consultation",
    "diagnostics": "Diagnostics",
    "billing_insurance": "Billing",
    "pharmacy": "Pharmacy",
}

# Capacities to match Live Occupancy
DEPARTMENT_CAPACITIES = {
    "registration": 15,
    "vision_lab": 12,
    "dilation_hall": 20,
    "diagnostics": 15,
    "consultation": 10,
    "pharmacy": 12,
    "billing_insurance": 10,
}


@router.get("/load-status", summary="Real-time hospital load status for all departments")
async def get_load_status(db: Session = Depends(get_db)):
    """
    Returns load level, waiting time, and queue size for each of the 7 hospital
    departments.  Uses waiting_model.pkl, arrival_model.pkl, and
    bottleneck_classification_model.pkl for classification.
    """
    # Collect global predictions (computed once)
    arrival_data = PredictionService.predict_arrival_rate(db)
    arrival_trend = arrival_data.get("trend", "stable")

    bottleneck_data = PredictionService.predict_bottleneck(db)
    bottleneck_by_zone = {}
    for pred in bottleneck_data.get("predictions", []):
        bottleneck_by_zone[pred["zone_name"]] = pred

    departments = []

    for zone_name, display_name in DEPARTMENT_DISPLAY_NAMES.items():
        # Per-department waiting time prediction
        wait_data = PredictionService.predict_department_wait(db, zone_name)
        waiting_minutes = wait_data.get("predicted_minutes") or 0.0

        # Queue size from zone occupancy (CV detection updates this)
        zone = db.query(Zone).filter(Zone.zone_name == zone_name).first()
        queue_size = zone.current_occupancy if zone else 0

        # Bottleneck classification for this department (preserved logic structure)
        bn_info = bottleneck_by_zone.get(zone_name, {})
        bn_class = bn_info.get("class_id", 0)

        # Classify load based on live occupancy percentage
        capacity = DEPARTMENT_CAPACITIES.get(zone_name, 10)
        load = _classify_load(queue_size, capacity)

        departments.append({
            "name": display_name,
            "zone_name": zone_name,
            "load_level": load["load_level"],
            "icon": load["icon"],
            "label": load["label"],
            "waiting_time": round(waiting_minutes),
            "queue_size": queue_size,
        })

    return {"departments": departments}
