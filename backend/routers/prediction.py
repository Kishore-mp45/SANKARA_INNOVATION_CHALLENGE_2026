"""
PatientPath AI - Prediction Router
==================================
API endpoints for AI forecasting.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from services.prediction_service import PredictionService
from services.staff_allocation_service import StaffAllocationService
from services.activity_service import ActivityService

router = APIRouter(prefix="/prediction", tags=["Prediction"])

@router.get(
    "/forecast",
    summary="Get AI Forecast",
    description="Get real-time AI predictions and decision support items."
)
async def get_forecast():
    """
    Get current AI predictions and recommended actions.
    
    Returns:
        JSON object containing 'predictions' list and 'decisions' list.
    """
    return PredictionService.get_forecast()

@router.get(
    "/average-wait",
    summary="Get Predicted Average Wait Time",
    description="Predicts average dwell time across all active zones using XGBoost model."
)
async def get_average_wait(db: Session = Depends(get_db)):
    """
    Get real-time average wait time prediction.
    
    Returns:
        JSON object with average_minutes, formatted string, and trend info.
    """
    return PredictionService.predict_average_wait(db)

@router.get(
    "/arrival-rate",
    summary="Get Predicted Arrival Rate",
    description="Predicts patient arrival rate for the next hour using XGBoost model."
)
async def get_arrival_rate(db: Session = Depends(get_db)):
    """
    Get real-time arrival rate prediction.
    
    Returns:
        JSON object with predicted_arrival_rate and trend info.
    """
    return PredictionService.predict_arrival_rate(db)

@router.get(
    "/exit-rate",
    summary="Get Predicted Exit Rate",
    description="Predicts patient exit rate for the current hour using XGBoost model."
)
async def get_exit_rate(db: Session = Depends(get_db)):
    """
    Get real-time exit rate prediction.

    Returns:
        JSON object with predicted_exit_rate and trend info.
    """
    return PredictionService.predict_exit_rate(db)

@router.get(
    "/bottleneck",
    summary="Get Bottleneck Classification",
    description="Classifies bottleneck severity for all 7 departments using XGBoost model."
)
async def get_bottleneck(db: Session = Depends(get_db)):
    """
    Get real-time bottleneck classification for all departments.

    Returns:
        JSON object with predictions per department and decision support items.
    """
    return PredictionService.predict_bottleneck(db)


@router.get(
    "/peak-hours/today",
    summary="Get Peak Hours of Today",
    description="Predicts the peak hour time range for today using the waiting time model and peak detection thresholds."
)
async def get_peak_hours_today(db: Session = Depends(get_db)):
    """
    Get predicted peak hours for today.

    Returns:
        JSON object with start_time, end_time, date, and peak department info.
    """
    return PredictionService.predict_peak_hours_today(db)


# ── Live Alerts Endpoint ──────────────────────────────────────────

@router.get(
    "/live-alerts",
    summary="Get Live Alerts from AI Models",
    description="Generates real-time alerts from bottleneck predictions and staff allocation recommendations."
)
async def get_live_alerts(db: Session = Depends(get_db)):
    """
    Get live alerts derived from AI prediction models.
    Combines bottleneck classification and staff allocation analysis.
    """
    alerts = []
    decisions = []
    now = __import__('datetime').datetime.now()

    # 1. Bottleneck alerts from classification model
    bottleneck_data = PredictionService.predict_bottleneck(db)
    for p in bottleneck_data.get("predictions", []):
        if p["class_id"] == 2:  # Severe bottleneck
            alerts.append({
                "id": f"bn-{p['zone_name']}",
                "msg": f"{p['department']} - Severe Bottleneck detected ({p['active_patients']} patients, {p['staff_count']} staff)",
                "severity": "critical",
                "icon": p["icon"],
                "confidence": p["confidence"],
                "department": p["department"],
                "source": "Bottleneck Model"
            })
        elif p["class_id"] == 1:  # Moderate bottleneck
            alerts.append({
                "id": f"bn-{p['zone_name']}",
                "msg": f"{p['department']} - Moderate Bottleneck ({p['active_patients']} patients, {p['staff_count']} staff)",
                "severity": "warning",
                "icon": p["icon"],
                "confidence": p["confidence"],
                "department": p["department"],
                "source": "Bottleneck Model"
            })

    # Collect decisions from bottleneck model
    for d in bottleneck_data.get("decisions", []):
        if d.get("type") != "normal":
            decisions.append(d)

    # 2. Staff allocation alerts
    staff_data = StaffAllocationService.get_all_recommendations(db)
    for dept in staff_data:
        deficit = dept.get("deficit", 0)
        if deficit >= 3:
            alerts.append({
                "id": f"staff-{dept.get('zone_name', '')}",
                "msg": f"{dept['department']} - Understaffed: {dept['current_staff']} staff on duty, optimal is {dept['optimal_staff']} (deficit: {deficit})",
                "severity": "critical",
                "icon": "fa-user-nurse",
                "department": dept["department"],
                "source": "Staff Allocation Model"
            })
        elif deficit >= 1:
            alerts.append({
                "id": f"staff-{dept.get('zone_name', '')}",
                "msg": f"{dept['department']} - Staff shortage: {dept['current_staff']}/{dept['optimal_staff']} staff (need {deficit} more)",
                "severity": "warning",
                "icon": "fa-user-nurse",
                "department": dept["department"],
                "source": "Staff Allocation Model"
            })

    # Add staff-related decisions for understaffed departments
    for dept in staff_data:
        if dept.get("deficit", 0) > 0:
            decisions.append({
                "title": f"{dept['department']} - Deploy Staff",
                "description": f"Deploy {dept['deficit']} additional staff to {dept['department']}. Currently {dept['current_staff']} staff for {dept['active_patients']} patients.",
                "action_label": "Deploy Staff",
                "type": "staff",
                "zone": dept.get("zone_name", ""),
            })

    # If no bottleneck decisions, add positive status
    if not decisions:
        decisions.append({
            "title": "All Clear",
            "description": "All departments operating within normal capacity. No immediate actions required.",
            "action_label": "Acknowledged",
            "type": "normal",
        })

    # Count severity levels
    critical_count = sum(1 for a in alerts if a["severity"] == "critical")
    warning_count = sum(1 for a in alerts if a["severity"] == "warning")

    return {
        "alerts": alerts,
        "decisions": decisions,
        "critical_count": critical_count,
        "warning_count": warning_count,
        "total_count": len(alerts),
        "timestamp": now.isoformat()
    }


# ── Staff Allocation Endpoints ──────────────────────────────────────

@router.get("/staff-recommendation")
async def get_all_staff_recommendations(db: Session = Depends(get_db)):
    """Get AI staff recommendations for all departments."""
    results = StaffAllocationService.get_all_recommendations(db)

    # Broadcast bottleneck alerts via WebSocket (best-effort)
    try:
        from routers.websocket import manager
        for rec in results:
            if rec.get("is_bottleneck") and rec.get("deficit", 0) > 0:
                await manager.broadcast({
                    "type": "staff_alert",
                    "data": {
                        "department": rec["department"],
                        "deficit": rec["deficit"],
                        "message": f"{rec['deficit']} staff member{'s' if rec['deficit'] > 1 else ''} needed in {rec['department']}."
                    }
                }, message_type="alerts")
    except Exception:
        pass

    return {"departments": results}


@router.get("/staff-recommendation/{department_name}")
async def get_staff_recommendation(department_name: str, db: Session = Depends(get_db)):
    """Get AI staff allocation recommendation for a specific department."""
    result = StaffAllocationService.predict_optimal_staff(db, department_name)
    if "error" in result and "Unknown" in result.get("error", ""):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/staff-checkin/{department_name}")
async def staff_checkin(department_name: str, db: Session = Depends(get_db)):
    """Check in a staff member to a department. Increments current staff by 1."""
    result = StaffAllocationService.checkin_staff(department_name, db)
    if "error" in result and "Unknown" in result.get("error", ""):
        raise HTTPException(status_code=404, detail=result["error"])

    # Log to Activity Service
    ActivityService.add_log(
        action="Staff Check-in",
        details=f"Staff checked in to {result['department']} — now {result['current_staff']} staff (optimal: {result['optimal_staff']})",
        severity="success",
        role="staff",
        user_id="Staff-User"
    )

    # Broadcast updated status via WebSocket (best-effort)
    try:
        from routers.websocket import manager
        await manager.broadcast({
            "type": "staff_update",
            "data": {
                "department": result["department"],
                "current_staff": result["current_staff"],
                "optimal_staff": result["optimal_staff"],
                "deficit": result["deficit"],
                "is_bottleneck": result["is_bottleneck"]
            }
        }, message_type="alerts")
    except Exception:
        pass

    return result
