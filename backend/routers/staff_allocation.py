"""Staff Allocation Router - AI-powered staff recommendation endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from services.staff_allocation_service import StaffAllocationService

router = APIRouter(prefix="/analytics", tags=["Staff Allocation"])


@router.get("/staff-recommendation/{department_name}")
async def get_staff_recommendation(department_name: str, db: Session = Depends(get_db)):
    """
    Get AI staff allocation recommendation for a specific department.
    Returns optimal staff, current staff, deficit, and bottleneck status.
    """
    result = StaffAllocationService.predict_optimal_staff(db, department_name)
    if "error" in result and "Unknown" in result.get("error", ""):
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.get("/staff-recommendation")
async def get_all_staff_recommendations(db: Session = Depends(get_db)):
    """Get AI staff recommendations for all departments."""
    results = StaffAllocationService.get_all_recommendations(db)

    # Broadcast bottleneck alerts via WebSocket
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
        pass  # WebSocket broadcast is best-effort

    return {"departments": results}


@router.post("/staff-checkin/{department_name}")
async def staff_checkin(department_name: str, db: Session = Depends(get_db)):
    """
    Check in a staff member to a department.
    Increments current staff by 1 and returns updated recommendation.
    """
    result = StaffAllocationService.checkin_staff(department_name, db)
    if "error" in result and "Unknown" in result.get("error", ""):
        raise HTTPException(status_code=404, detail=result["error"])

    # Broadcast updated status via WebSocket
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
