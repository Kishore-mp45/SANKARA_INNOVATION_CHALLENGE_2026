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
