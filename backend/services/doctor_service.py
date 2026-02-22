from datetime import datetime
from sqlalchemy.orm import Session
from models.doctor import Doctor, DoctorStatus, ConsultationLog
from services.patient_service import PatientService
from fastapi import HTTPException
from models.patient import Patient, PatientStatus

class DoctorService:
    @staticmethod
    def get_or_create_doctor(db: Session, doctor_id: int, name: str = "Dr. Unknown"):
        try:
            doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
            if not doctor:
                doctor = Doctor(id=doctor_id, name=name, status=DoctorStatus.OFFLINE)
                db.add(doctor)
                db.commit()
                db.refresh(doctor)
            return doctor
        except Exception as e:
            print(f"Error in DoctorService.get_or_create_doctor: {e}")
            raise e

    @staticmethod
    def check_in(db: Session, doctor_id: int, name: str):
        try:
            doctor = DoctorService.get_or_create_doctor(db, doctor_id, name)
            doctor.status = DoctorStatus.ONLINE
            doctor.last_check_in = datetime.now()
            db.commit()
            db.refresh(doctor)
            return doctor
        except Exception as e:
            print(f"Error in DoctorService.check_in: {e}")
            db.rollback()
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    def check_out(db: Session, doctor_id: int):
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        doctor.status = DoctorStatus.OFFLINE
        doctor.last_check_out = datetime.now()
        db.commit()
        return doctor

    @staticmethod
    def start_consultation(db: Session, doctor_id: int, patient_id: str):
        # Verify doctor exists and is online
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if not doctor or doctor.status == DoctorStatus.OFFLINE:
            raise HTTPException(status_code=400, detail="Doctor must be online to start consultation")

        # Verify patient exists
        patient = db.query(Patient).filter(Patient.tracking_id == patient_id).first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found")

        # Create consultation log
        log = ConsultationLog(
            doctor_id=doctor_id,
            patient_id=patient_id,
            start_time=datetime.now()
        )
        db.add(log)

        # Move patient to consultation zone so dashboard reflects the update
        from models.zone import Zone
        old_zone_name = patient.current_zone
        new_zone_name = "consultation"

        if old_zone_name != new_zone_name:
            # Decrement old zone occupancy
            if old_zone_name:
                old_zone = db.query(Zone).filter(Zone.zone_name == old_zone_name).first()
                if old_zone and old_zone.current_occupancy > 0:
                    old_zone.current_occupancy -= 1

            # Increment consultation zone occupancy
            consult_zone = db.query(Zone).filter(Zone.zone_name == new_zone_name).first()
            if consult_zone:
                consult_zone.current_occupancy += 1

        patient.current_zone = new_zone_name
        patient.last_action = "Doctor Consultation Started"
        patient.updated_at = datetime.now()
        patient.status = PatientStatus("in_room")

        # Append to action_history
        import json
        history = json.loads(patient.action_history) if patient.action_history else []
        history.append({
            "action": "Doctor Consultation Started",
            "zone": "consultation",
            "timestamp": datetime.now().isoformat()
        })
        patient.action_history = json.dumps(history)
        
        db.commit()
        db.refresh(log)
        return log

    @staticmethod
    def complete_consultation(db: Session, doctor_id: int, patient_id: str, notes: str, next_stage: str):
        # Find active consultation log
        log = db.query(ConsultationLog).filter(
            ConsultationLog.doctor_id == doctor_id,
            ConsultationLog.patient_id == patient_id,
            ConsultationLog.end_time == None
        ).order_by(ConsultationLog.start_time.desc()).first()

        if log:
            log.end_time = datetime.now()
            log.notes = notes

        # Commit the consultation log first (independent of patient update)
        try:
            db.commit()
        except Exception as e:
            db.rollback()
            print(f"Error saving consultation log: {e}")

        # Update Patient Stage separately
        try:
            PatientService.update_patient_stage(
                db=db,
                tracking_id=patient_id,
                department="consultation",
                action="Doctor Consultation Ended",
                next_department=next_stage,
                staff_id=str(doctor_id)
            )
        except Exception as e:
            print(f"Warning updating patient stage: {e}")
            try:
                db.rollback()
            except Exception:
                pass
            return {"status": "partial", "message": f"Consultation saved but patient update failed: {str(e)}"}

        return {"status": "success", "message": "Consultation completed"}
