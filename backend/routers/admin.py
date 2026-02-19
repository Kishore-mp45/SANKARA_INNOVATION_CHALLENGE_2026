from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from typing import List, Optional
from services.activity_service import ActivityService
from services.patient_service import PatientService
from services.zone_service import ZoneService
from database import get_db
from sqlalchemy.orm import Session
from datetime import datetime

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

@router.get("/activity")
async def get_activity(limit: int = 100, role: Optional[str] = None):
    """Get recent activity logs."""
    return {
        "logs": ActivityService.get_logs(limit, role)
    }

@router.get("/export")
async def export_activity():
    """Export activity logs as CSV."""
    csv_content = ActivityService.export_logs_csv()
    filename = f"activity_log_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return PlainTextResponse(
        content=csv_content,
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
