from fastapi import APIRouter, Depends, HTTPException, Body
from sqlalchemy.orm import Session
from database import get_db
from services.doctor_service import DoctorService
from typing import Optional
from pydantic import BaseModel

router = APIRouter(prefix="/doctor", tags=["Doctor"])

class StatusUpdate(BaseModel):
    doctor_id: int
    name: Optional[str] = "Dr. Unknown"

class ConsultationStart(BaseModel):
    doctor_id: int
    patient_id: str

class ConsultationComplete(BaseModel):
    doctor_id: int
    patient_id: str
    notes: Optional[str] = ""
    next_stage: str

@router.post("/check-in")
def check_in(data: StatusUpdate, db: Session = Depends(get_db)):
    """Doctor check-in."""
    return DoctorService.check_in(db, data.doctor_id, data.name)

@router.post("/check-out")
def check_out(data: StatusUpdate, db: Session = Depends(get_db)):
    """Doctor check-out."""
    return DoctorService.check_out(db, data.doctor_id)

@router.post("/consult/start")
def start_consultation(data: ConsultationStart, db: Session = Depends(get_db)):
    """Start patient consultation."""
    return DoctorService.start_consultation(db, data.doctor_id, data.patient_id)

@router.post("/consult/complete")
def complete_consultation(data: ConsultationComplete, db: Session = Depends(get_db)):
    """Complete consultation and update patient stage."""
    return DoctorService.complete_consultation(db, data.doctor_id, data.patient_id, data.notes, data.next_stage)

@router.get("/status/{doctor_id}")
def get_status(doctor_id: int, db: Session = Depends(get_db)):
    """Get doctor status."""
    return DoctorService.get_or_create_doctor(db, doctor_id)


@router.get("/workload/{doctor_id}")
def get_workload(doctor_id: int, db: Session = Depends(get_db)):
    """Get doctor's daily workload: patients consulted today and average consultation time."""
    return DoctorService.get_workload(db, doctor_id)


@router.get("/consultation-trend/{doctor_id}")
def get_consultation_trend(doctor_id: int, db: Session = Depends(get_db)):
    """Get today's hourly doctor consultation trend."""
    return DoctorService.get_consultation_trend(db, doctor_id)


@router.get("/last-activity/{doctor_id}")
def get_last_activity(doctor_id: int, db: Session = Depends(get_db)):
    """Get time since doctor's last action."""
    return DoctorService.get_last_activity(db, doctor_id)


@router.get("/workload-status/{doctor_id}")
def get_workload_status(doctor_id: int, db: Session = Depends(get_db)):
    """Get doctor's workload status indicator (Low/Moderate/High)."""
    return DoctorService.get_workload_status(db, doctor_id)


@router.get("/stats/{doctor_id}")
def get_stats(doctor_id: int, db: Session = Depends(get_db)):
    """Get doctor's last update time and total actions count."""
    return DoctorService.get_stats(db, doctor_id)


@router.get("/activity-history/{doctor_id}")
def get_activity_history(doctor_id: int, db: Session = Depends(get_db)):
    """Get doctor's full activity history, newest first."""
    return DoctorService.get_activity_history(db, doctor_id)
