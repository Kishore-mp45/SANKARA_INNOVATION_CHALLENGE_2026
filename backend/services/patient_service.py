"""Patient Service"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.patient import Patient, PatientStatus
from schemas.patient import PatientCreate, PatientUpdate


class PatientService:
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Patient]:
        return db.query(Patient).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_id(db: Session, patient_id: int) -> Optional[Patient]:
        return db.query(Patient).filter(Patient.id == patient_id).first()
    
    @staticmethod
    def get_by_tracking_id(db: Session, tracking_id: str) -> Optional[Patient]:
        return db.query(Patient).filter(Patient.tracking_id == tracking_id).first()
    
    @staticmethod
    def get_by_zone(db: Session, zone_name: str) -> List[Patient]:
        return db.query(Patient).filter(Patient.current_zone == zone_name).all()
    
    @staticmethod
    def get_active(db: Session) -> List[Patient]:
        return db.query(Patient).filter(Patient.status != PatientStatus.EXITED).all()
    
    @staticmethod
    def create(db: Session, patient_data: PatientCreate) -> Patient:
        patient = Patient(
            name=patient_data.name,
            mobile=patient_data.mobile,
            tracking_id=patient_data.tracking_id,
            status=patient_data.status,
            current_zone=patient_data.current_zone,
            entry_time=datetime.utcnow()
        )
        db.add(patient)
        db.commit()
        db.refresh(patient)
        return patient
    
    @staticmethod
    def update(db: Session, patient_id: int, patient_data: PatientUpdate) -> Optional[Patient]:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return None
        
        update_data = patient_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(patient, key, value)
        
        patient.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(patient)
        return patient
    
    @staticmethod
    def delete(db: Session, patient_id: int) -> bool:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if not patient:
            return False
        db.delete(patient)
        db.commit()
        return True
    
    @staticmethod
    def count(db: Session) -> int:
        return db.query(Patient).count()
    
    @staticmethod
    def count_active(db: Session) -> int:
        return db.query(Patient).filter(Patient.status != PatientStatus.EXITED).count()
