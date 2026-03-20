from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from typing import List, Optional
from services.activity_service import ActivityService
from services.patient_service import PatientService
from services.zone_service import ZoneService
from database import get_db
from models.patient import Patient
from models.user import User
from models.escalation import Escalation, EscalationStatus
from models.occupancy import OccupancyLog
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import json


class StaffAssignment(BaseModel):
    staff_user_id: int
    department: str


class DeployStaffRequest(BaseModel):
    staff_user_id: int
    target_department: str
    message: Optional[str] = None

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

@router.get("/resources/status")
async def get_resource_status():
    """
    Returns realistic, deterministic resource allocation data.
    Instead of jumping randomly every second, this uses the current hour 
    and a 15-minute bucket as a seed to generate stable numbers that trend slowly.
    """
    now = datetime.now()
    # Create a stable seed based on the current 15-minute interval
    seed_val = now.day * 100 + now.hour * 10 + (now.minute // 15)
    
    # Use standard library random with a seed for stable dummy data
    import random
    rng = random.Random(seed_val)
    
    totalBeds = 120
    # Base beds trend down during the day, up at night (rough simulation)
    base_beds = 40 if now.hour < 8 or now.hour > 20 else 20
    availBeds = base_beds + rng.randint(-10, 10)
    availBeds = max(5, min(availBeds, totalBeds))

    totalRooms = 25
    base_rooms = 5 if now.hour < 8 or now.hour > 20 else 18
    busyRooms = base_rooms + rng.randint(-3, 3)
    busyRooms = max(0, min(busyRooms, totalRooms))

    totalDoctors = 18
    base_docs = 14 if now.hour > 8 and now.hour < 18 else 4
    freeDoctors = base_docs + rng.randint(-2, 2)
    freeDoctors = max(0, min(freeDoctors, totalDoctors))

    totalStaff = 35
    base_staff = 25 if now.hour > 8 and now.hour < 18 else 10
    freeStaff = base_staff + rng.randint(-4, 4)
    freeStaff = max(0, min(freeStaff, totalStaff))

    totalEquip = 40
    base_equip = 30 if now.hour > 8 and now.hour < 18 else 15
    activeEquip = base_equip + rng.randint(-5, 5)
    activeEquip = max(0, min(activeEquip, totalEquip))
    equipUsage = int((activeEquip / totalEquip) * 100)
    
    # Generate 10 previous data points for the frontend sparklines
    # by simulating the previous 10 15-minute intervals
    trend_beds = []
    trend_rooms = []
    trend_staff = []
    
    # helper for historical simulation
    def get_hist_val(h, m, base_val, variation):
        seed = now.day * 100 + h * 10 + (m // 15)
        r = random.Random(seed)
        return max(0, base_val + r.randint(-variation, variation))
        
    for i in range(10, 0, -1):
        hist_time = now - timedelta(minutes=15 * i)
        th = hist_time.hour
        tm = hist_time.minute
        
        hb = 40 if th < 8 or th > 20 else 20
        hr = 5 if th < 8 or th > 20 else 18
        hs = 25 if th > 8 and th < 18 else 10
        
        trend_beds.append(get_hist_val(th, tm, hb, 10))
        trend_rooms.append(get_hist_val(th, tm, hr, 3))
        trend_staff.append(get_hist_val(th, tm, hs, 4))
        
    trend_beds.append(availBeds)
    trend_rooms.append(busyRooms)
    trend_staff.append(freeStaff)

    return {
        "beds": {"available": availBeds, "total": totalBeds, "trend": trend_beds},
        "rooms": {"busy": busyRooms, "total": totalRooms, "trend": trend_rooms},
        "doctors": {"free": freeDoctors, "total": totalDoctors},
        "staff": {"free": freeStaff, "total": totalStaff, "trend": trend_staff},
        "equipment": {"usage_percent": equipUsage, "active": activeEquip, "total": totalEquip}
    }


@router.post("/assign-staff")
async def assign_staff(body: StaffAssignment, db: Session = Depends(get_db)):
    """Assign a staff member to a department and send real-time notification."""
    staff = db.query(User).filter(User.id == body.staff_user_id, User.role == "staff").first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    dept_name = DEPT_DISPLAY.get(body.department, body.department)

    # Update department in user record
    staff.department = body.department
    db.commit()

    # Broadcast notification via WebSocket to that specific staff
    try:
        from routers.websocket import manager
        await manager.send_to_user(staff.generated_id, {
            "type": "staff_assignment",
            "data": {
                "message": f"You have been assigned to {dept_name}",
                "department": body.department,
                "department_display": dept_name,
            },
            "timestamp": datetime.now().isoformat()
        })
    except Exception:
        pass  # WebSocket notification is best-effort

    # Also broadcast to all admin connections
    try:
        from routers.websocket import manager
        await manager.broadcast({
            "type": "staff_assignment",
            "data": {
                "staff_id": staff.generated_id,
                "staff_name": staff.username,
                "department": dept_name,
            },
            "timestamp": datetime.now().isoformat()
        }, message_type="alerts")
    except Exception:
        pass

    return {
        "message": f"Staff '{staff.username}' assigned to {dept_name}",
        "staff_id": staff.generated_id,
        "department": body.department,
    }


@router.get("/available-staff")
async def get_available_staff(
    exclude_department: Optional[str] = Query(None, description="Exclude staff from this department"),
    db: Session = Depends(get_db),
):
    """Get list of approved staff available for deployment, with pending deployment status."""
    from models.notification import Notification

    query = db.query(User).filter(User.role == "staff", User.status == "approved")

    if exclude_department:
        query = query.filter(User.department != exclude_department)

    staff_list = query.all()

    # Look up pending deployment notifications for each staff
    pending_notifs = db.query(Notification).filter(
        Notification.type == "deployment",
        Notification.status == "pending",
    ).all()
    # Map recipient_id -> notification info
    pending_map = {}
    for n in pending_notifs:
        pending_map[n.recipient_id] = {
            "notification_id": n.id,
            "target_department": n.target_department,
            "target_display": DEPT_DISPLAY.get(n.target_department, n.target_department),
        }

    result = []
    for s in staff_list:
        entry = {
            "id": s.id,
            "username": s.username,
            "generated_id": s.generated_id,
            "department": s.department,
            "department_display": DEPT_DISPLAY.get(s.department, s.department),
            "mobile": s.mobile,
            "deployment_pending": False,
            "pending_target": None,
        }
        if s.generated_id in pending_map:
            entry["deployment_pending"] = True
            entry["pending_target"] = pending_map[s.generated_id]["target_display"]
        result.append(entry)

    return {
        "available_staff": result,
        "count": len(result),
    }


@router.post("/deploy-staff")
async def deploy_staff(body: DeployStaffRequest, db: Session = Depends(get_db)):
    """Deploy a staff member to a target department. Sends real-time notification."""
    from models.notification import Notification

    staff = db.query(User).filter(User.id == body.staff_user_id, User.role == "staff").first()
    if not staff:
        raise HTTPException(status_code=404, detail="Staff member not found")

    target_display = DEPT_DISPLAY.get(body.target_department, body.target_department)
    source_display = DEPT_DISPLAY.get(staff.department, staff.department)

    # Create notification record
    notif = Notification(
        recipient_id=staff.generated_id,
        sender_id="ADMIN",
        type="deployment",
        title=f"Deployment Request: {target_display}",
        message=body.message or f"You are requested to assist at {target_display} department. Current assignment: {source_display}.",
        target_department=body.target_department,
        status="pending",
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)

    # Send real-time WebSocket notification
    try:
        from routers.websocket import manager
        await manager.send_to_user(staff.generated_id, {
            "type": "deployment_request",
            "data": notif.to_dict(),
            "timestamp": datetime.now().isoformat()
        })
    except Exception:
        pass

    return {
        "message": f"Deployment notification sent to {staff.username}",
        "notification": notif.to_dict(),
    }


@router.get("/deployment-status")
async def get_deployment_status(
    target_department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get deployment notification statuses. Used by admin to poll for acceptance/rejection."""
    from models.notification import Notification

    query = db.query(Notification).filter(Notification.type == "deployment")
    if target_department:
        query = query.filter(Notification.target_department == target_department)

    notifs = query.order_by(Notification.created_at.desc()).limit(50).all()

    pending_count = sum(1 for n in notifs if n.status == "pending")
    accepted_count = sum(1 for n in notifs if n.status == "accepted")

    return {
        "deployments": [n.to_dict() for n in notifs],
        "pending_count": pending_count,
        "accepted_count": accepted_count,
    }


@router.get("/notifications/{recipient_id}")
async def get_notifications(
    recipient_id: str,
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get notifications for a specific staff member."""
    from models.notification import Notification

    query = db.query(Notification).filter(Notification.recipient_id == recipient_id)
    if status:
        query = query.filter(Notification.status == status)

    notifs = query.order_by(Notification.created_at.desc()).limit(50).all()
    return {"notifications": [n.to_dict() for n in notifs], "count": len(notifs)}


@router.post("/notifications/{notification_id}/respond")
async def respond_to_notification(
    notification_id: int,
    action: str = Query(..., description="accepted or rejected"),
    db: Session = Depends(get_db),
):
    """Staff responds to a deployment notification. On accept, performs check-in to target department."""
    from models.notification import Notification
    from services.staff_allocation_service import StaffAllocationService

    notif = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    if action not in ("accepted", "rejected"):
        raise HTTPException(status_code=400, detail="Action must be 'accepted' or 'rejected'")

    notif.status = action
    notif.responded_at = datetime.utcnow()
    db.commit()

    checkin_result = None

    # On acceptance, perform the actual staff check-in to target department
    if action == "accepted" and notif.target_department:
        checkin_result = StaffAllocationService.checkin_staff(
            notif.target_department, db, staff_id=notif.recipient_id
        )

        # Broadcast the staff update via WebSocket so admin alerts refresh
        try:
            from routers.websocket import manager
            await manager.broadcast({
                "type": "staff_update",
                "data": {
                    "department": checkin_result.get("department", notif.target_department),
                    "current_staff": checkin_result.get("current_staff", 0),
                    "optimal_staff": checkin_result.get("optimal_staff", 0),
                    "deficit": checkin_result.get("deficit", 0),
                    "is_bottleneck": checkin_result.get("is_bottleneck", False),
                    "event": "deployment_accepted",
                    "staff_id": notif.recipient_id,
                }
            }, message_type="alerts")
        except Exception:
            pass

    return {
        "message": f"Notification {action}",
        "notification": notif.to_dict(),
        "checkin_result": checkin_result,
    }
