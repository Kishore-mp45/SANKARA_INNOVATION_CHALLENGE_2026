from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from typing import List, Optional
from services.activity_service import ActivityService
from services.patient_service import PatientService
from services.zone_service import ZoneService
from database import get_db
from models.patient import Patient
from sqlalchemy.orm import Session
from datetime import datetime
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
