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
            entry_time=datetime.now()
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
        
        patient.updated_at = datetime.now()
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

    @staticmethod
    def update_patient_stage(
        db: Session,
        tracking_id: str,
        department: str,
        action: str,
        next_department: Optional[str] = None,
        staff_id: Optional[str] = None,
        name: Optional[str] = None,
        mobile: Optional[str] = None
    ):
        """
        Centrally update patient stage, ensuring activity logging and alerts.
        """
        # Local imports to avoid circular dependency
        from services.zone_service import ZoneService
        from services.activity_service import ActivityService
        from services.alert_service import AlertService
        from schemas.patient import PatientCreate
        from models.patient import PatientStatus
        
        zone_service = ZoneService(db)
        
        # 1. Verify/Create Patient
        patient = PatientService.get_by_tracking_id(db, tracking_id)
        if not patient:
            # Auto-create for Registration workflow
            # Ensure zone exists first
            start_zone = zone_service.get_zone_by_name(department)
            if not start_zone:
                 raise Exception(f"Initial Department '{department}' not found")

            new_patient = PatientCreate(
                name=name or "New Patient",
                mobile=mobile,
                tracking_id=tracking_id,
                status=PatientStatus.ENTERED,
                current_zone=department
            )
            
            patient = PatientService.create(db, new_patient)
            
            # Increment initial zone occupancy
            if start_zone.current_occupancy < start_zone.capacity_limit * 2:
                start_zone.current_occupancy += 1
                db.commit()
        else:
            # Update details if provided
            if department == "registration" and (name or mobile):
                if name: patient.name = name
                if mobile: patient.mobile = mobile
                db.commit()

        # 2. Update Zone if next_department is provided
        if next_department:
            if next_department == "exit":
                patient.status = PatientStatus.EXITED
                patient.exit_time = datetime.now()
                
                # Decrease occupancy of old zone if it exists
                if patient.current_zone:
                    old_zone = zone_service.get_zone_by_name(patient.current_zone)
                    if old_zone and old_zone.current_occupancy > 0:
                        old_zone.current_occupancy -= 1
                
                patient.current_zone = "exit"
            else:
                target_zone = zone_service.get_zone_by_name(next_department)
                if not target_zone:
                     raise Exception(f"Department '{next_department}' not found")
                
                # Move patient logic
                if patient.current_zone and patient.current_zone != next_department:
                    old_zone = zone_service.get_zone_by_name(patient.current_zone)
                    if old_zone and old_zone.current_occupancy > 0:
                        old_zone.current_occupancy -= 1
                    target_zone.current_occupancy += 1
                
                patient.current_zone = next_department

        # 3. Update Timestamp & Action
        patient.updated_at = datetime.now()
        patient.last_action = action

        # Append to action_history
        import json
        history = json.loads(patient.action_history) if patient.action_history else []
        history.append({
            "action": action,
            "zone": next_department or department,
            "timestamp": datetime.now().isoformat()
        })
        patient.action_history = json.dumps(history)

        db.commit()
        db.refresh(patient)
        
        # Check alerts
        if next_department:
            try:
                alert_service = AlertService(db)
                # Re-fetch target zone to get updated occupancy
                tz = zone_service.get_zone_by_name(next_department)
                if tz: alert_service.check_zone_thresholds(tz)
            except Exception as e:
                print(f"Failed to check alerts: {e}")

        # 4. Log Action
        target_dept = next_department
        loc_desc = department if (not target_dept or target_dept == department) else f"{department} -> {target_dept}"

        ActivityService.add_log(
            action=action or f"Update Status: {department}",
            details=f"{tracking_id} | {loc_desc}",
            severity="success",
            role="Staff",
            user_id=staff_id or "Staff-User"
        )

        return patient
