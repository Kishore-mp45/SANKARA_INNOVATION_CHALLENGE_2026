from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from typing import List, Optional
from services.activity_service import ActivityService
from services.patient_service import PatientService
from services.zone_service import ZoneService
from database import get_db
from models.patient import Patient
from models.escalation import Escalation, EscalationStatus
from models.occupancy import OccupancyLog
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

DEPT_DISPLAY = {
    "registration": "Registration",
    "vision_lab": "Vision Lab",
    "dilation_hall": "Dilation Hall",
    "consultation": "Consultation",
    "diagnostics": "Diagnostics",
    "pharmacy": "Pharmacy",
    "billing_insurance": "Billing & Insurance",
    "exit": "Exit",
}

@router.get("/activity")
async def get_activity(limit: int = 100, role: Optional[str] = None, db: Session = Depends(get_db)):
    """Get recent activity logs from patient action_history in the database."""
    patients = db.query(Patient).filter(
        Patient.action_history != None,
        Patient.action_history != "[]"
    ).all()

    all_logs = []
    for p in patients:
        try:
            history = json.loads(p.action_history) if p.action_history else []
        except (json.JSONDecodeError, TypeError):
            continue

        for entry in history:
            zone_key = entry.get("zone", "")
            dept_name = DEPT_DISPLAY.get(zone_key, zone_key.replace("_", " ").title())
            action_text = entry.get("action", "Unknown Action")

            all_logs.append({
                "id": int(datetime.fromisoformat(entry["timestamp"]).timestamp() * 1000) if entry.get("timestamp") else 0,
                "timestamp": entry.get("timestamp", ""),
                "action": action_text,
                "details": f"{p.name} ({p.tracking_id}) - {dept_name}",
                "severity": "success",
                "role": "staff",
                "user_id": "Staff"
            })

    # Sort by timestamp descending (newest first)
    all_logs.sort(key=lambda x: x["timestamp"], reverse=True)

    return {
        "logs": all_logs[:limit]
    }

@router.get("/export")
async def export_activity(db: Session = Depends(get_db)):
    """Export patient activity logs as CSV from database."""
    import csv as csv_mod
    import io

    patients = db.query(Patient).filter(
        Patient.action_history != None,
        Patient.action_history != "[]"
    ).all()

    output = io.StringIO()
    writer = csv_mod.writer(output)
    writer.writerow(['Timestamp', 'Patient', 'Tracking ID', 'Action', 'Department'])

    rows = []
    for p in patients:
        try:
            history = json.loads(p.action_history) if p.action_history else []
        except (json.JSONDecodeError, TypeError):
            continue
        for entry in history:
            zone_key = entry.get("zone", "")
            dept_name = DEPT_DISPLAY.get(zone_key, zone_key.replace("_", " ").title())
            rows.append((
                entry.get("timestamp", ""),
                p.name,
                p.tracking_id,
                entry.get("action", ""),
                dept_name
            ))

    rows.sort(key=lambda x: x[0], reverse=True)
    for row in rows:
        writer.writerow(row)

    filename = f"activity_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return PlainTextResponse(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

@router.get("/dashboard-stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Get aggregated stats for Admin Dashboard widgets."""
    
    # 1. Active Patients
    active_count = PatientService.count_active(db)
    
    # 2. Zone Distribution (only the 7 application departments)
    VALID_DEPTS = [
        "registration", "vision_lab", "dilation_hall",
        "diagnostics", "consultation", "pharmacy", "billing_insurance"
    ]
    zone_svc = ZoneService(db)
    zones = zone_svc.get_all()
    zone_stats = [
        {"name": z.zone_name, "count": z.current_occupancy}
        for z in zones if z.zone_name in VALID_DEPTS
    ]
    
    # 3. System Status (Mock/Real)
    # real system status is handled by /system/status, but we can aggregate here
    
    return {
        "active_patients": active_count,
        "zone_distribution": zone_stats,
        "critical_alerts": 0, # Placeholder for now unless we hook alert service
        "system_health": "Optimal"
    }


@router.get("/escalations")
async def get_escalations(
    status: Optional[str] = Query(None, description="Filter: OPEN, IN_PROGRESS, RESOLVED"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """Get escalation reports for the Admin Escalation Panel."""
    query = db.query(Escalation).order_by(Escalation.timestamp.desc())
    if status:
        try:
            status_enum = EscalationStatus(status)
            query = query.filter(Escalation.status == status_enum)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    rows = query.limit(limit).all()
    return {"escalations": [r.to_dict() for r in rows]}

from pydantic import BaseModel

class EscalationStatusUpdate(BaseModel):
    status: EscalationStatus

@router.put("/escalations/{escalation_id}/status")
async def update_escalation_status(
    escalation_id: int,
    body: EscalationStatusUpdate,
    db: Session = Depends(get_db)
):
    """Update the status of an escalation report."""
    escalation = db.query(Escalation).filter(Escalation.id == escalation_id).first()
    if not escalation:
        raise HTTPException(status_code=404, detail="Escalation not found")
        
    escalation.status = body.status
    db.commit()
    db.refresh(escalation)
    return {
        "message": "Escalation status updated",
        "escalation": escalation.to_dict()
    }


@router.get("/hourly-occupancy")
async def hourly_occupancy(db: Session = Depends(get_db)):
    """
    Return aggregated occupancy data across all zones for the past 5 hours
    at 30-minute intervals, for the admin Hourly Occupancy chart.
    """
    now = datetime.now()
    cur_min = 0 if now.minute < 30 else 30
    slot_time = now.replace(minute=cur_min, second=0, microsecond=0)
    start_time = slot_time - timedelta(hours=5)

    # Generate all 30-min time slots
    slots: list[str] = []
    t = start_time
    while t <= slot_time:
        slots.append(t.strftime("%H:%M"))
        t += timedelta(minutes=30)

    # Fetch all occupancy logs from the past 5 hours (all zones)
    logs = (
        db.query(OccupancyLog)
        .filter(OccupancyLog.timestamp >= start_time)
        .order_by(OccupancyLog.timestamp.asc())
        .all()
    )

    # Aggregate into 30-minute buckets: store logs to group by zone later
    half_hour_buckets: dict[str, list[OccupancyLog]] = {}
    for log in logs:
        if not log.timestamp:
            continue
        m = log.timestamp.minute
        bucket_min = "00" if m < 30 else "30"
        bucket_key = log.timestamp.strftime("%H:") + bucket_min
        half_hour_buckets.setdefault(bucket_key, []).append(log)

    # Build result for all slots, fill missing with 0
    data = []
    for slot in slots:
        if slot in half_hour_buckets:
            # Group by zone to get average per zone, then sum them up
            logs_in_slot = half_hour_buckets[slot] # This is a list of log objects now, not ints
            
            zone_averages = {}
            for log in logs_in_slot:
                zone_averages.setdefault(log.zone_name, []).append(log.people_count)
            
            total_slot_occupancy = 0
            for zone_name, counts in zone_averages.items():
                total_slot_occupancy += round(sum(counts) / len(counts))

            data.append({
                "time": slot,
                "avg_occupancy": total_slot_occupancy,
            })
        else:
            data.append({
                "time": slot,
                "avg_occupancy": 0,
            })

    return {"occupancy_trend": data}


# ---- Staff Name Pools per Department ----
import random as _random

_STAFF_NAMES = {
    "registration": [("ADM-R01", "Admin"), ("ADM-R02", "Admin"), ("NUR-R01", "Nurse")],
    "vision_lab": [("DOC-V01", "Doctor"), ("NUR-V01", "Nurse"), ("NUR-V02", "Nurse")],
    "dilation_hall": [("NUR-D01", "Nurse"), ("NUR-D02", "Nurse"), ("DOC-D01", "Doctor")],
    "diagnostics": [("DOC-X01", "Doctor"), ("NUR-X01", "Nurse"), ("NUR-X02", "Nurse")],
    "consultation": [("DOC-C01", "Doctor"), ("DOC-C02", "Doctor"), ("NUR-C01", "Nurse")],
    "pharmacy": [("NUR-P01", "Nurse"), ("NUR-P02", "Nurse"), ("ADM-P01", "Admin")],
    "billing_insurance": [("ADM-B01", "Admin"), ("ADM-B02", "Admin"), ("ADM-B03", "Admin")],
}

_ACTION_MAP = {
    "Moved to Registration": "Processed patient registration",
    "Check-In Completed": "Completed patient check-in",
    "ID Card Assigned": "Assigned patient ID card",
    "Moved to Vision Lab": "Started vision screening",
    "Vision Screening Started": "Conducted vision test",
    "Moved to Dilation Hall": "Administered dilation drops",
    "Dilation Started": "Monitored dilation process",
    "Moved to Diagnostics": "Initiated diagnostic tests",
    "Diagnostic Tests Started": "Performed diagnostic examination",
    "Moved to Consultation": "Prepared patient for consultation",
    "Treatment Started": "Started treatment procedure",
    "Consultation Completed": "Completed patient consultation",
    "Moved to Pharmacy": "Dispensed prescribed medication",
    "Medicine Dispensed": "Verified and handed over medicines",
    "Moved to Billing & Insurance": "Processed billing",
    "Payment Processed": "Completed payment processing",
    "Discharged": "Processed patient discharge",
}

_rng = _random.Random(42)  # Deterministic seed for consistent staff assignment


@router.get("/staff-activity-logs")
async def get_staff_activity_logs(
    department: Optional[str] = Query(None, description="Filter by department key"),
    role: Optional[str] = Query(None, description="Filter by role: Doctor, Nurse, Admin"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """
    Generate staff activity logs derived from patient action_history.
    Maps each patient action to a simulated staff member in that department.
    """
    patients = db.query(Patient).filter(
        Patient.action_history != None,
        Patient.action_history != "[]"
    ).all()

    all_logs = []
    for p in patients:
        try:
            history = json.loads(p.action_history) if p.action_history else []
        except (json.JSONDecodeError, TypeError):
            continue

        for entry in history:
            zone_key = entry.get("zone", "")
            action_text = entry.get("action", "Unknown Action")
            timestamp = entry.get("timestamp", "")

            if department and zone_key != department:
                continue

            # Pick a staff member for this department
            staff_pool = _STAFF_NAMES.get(zone_key, [("ADM-001", "Admin")])
            # Use hash of patient + timestamp for deterministic but varied assignment
            idx = hash(f"{p.tracking_id}:{timestamp}") % len(staff_pool)
            staff_id, staff_role = staff_pool[idx]

            if role and staff_role.lower() != role.lower():
                continue

            dept_display = DEPT_DISPLAY.get(zone_key, zone_key.replace("_", " ").title())
            staff_action = _ACTION_MAP.get(action_text, action_text)

            all_logs.append({
                "timestamp": timestamp,
                "staff_id": staff_id,
                "role": staff_role,
                "action": staff_action,
                "department": dept_display,
                "patient": f"{p.name} ({p.tracking_id})",
            })

    all_logs.sort(key=lambda x: x["timestamp"], reverse=True)
    return {"logs": all_logs[:limit]}
