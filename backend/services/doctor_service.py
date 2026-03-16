from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, cast, Date
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

    @staticmethod
    def get_workload(db: Session, doctor_id: int):
        """Get doctor's daily workload stats: patients consulted today, avg time, hourly breakdown."""
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        # All completed consultations for this doctor today
        today_logs = db.query(ConsultationLog).filter(
            ConsultationLog.doctor_id == doctor_id,
            ConsultationLog.start_time >= today_start,
            ConsultationLog.start_time <= today_end,
            ConsultationLog.end_time.isnot(None)
        ).all()

        patients_consulted_today = len(today_logs)

        # Calculate average consultation time in minutes
        total_minutes = 0
        for log in today_logs:
            duration = (log.end_time - log.start_time).total_seconds() / 60.0
            total_minutes += duration

        average_consultation_time = round(total_minutes / patients_consulted_today) if patients_consulted_today > 0 else 0

        # Hourly breakdown (0-23)
        hourly_counts = {}
        for log in today_logs:
            hour = log.start_time.hour
            key = f"{hour:02d}:00"
            hourly_counts[key] = hourly_counts.get(key, 0) + 1

        return {
            "doctor_id": f"D{doctor_id}",
            "patients_consulted_today": patients_consulted_today,
            "average_consultation_time": average_consultation_time,
            "hourly_breakdown": hourly_counts
        }

    @staticmethod
    def get_consultation_trend(db: Session, doctor_id: int):
        """Get today's completed consultation counts grouped by hour for a doctor."""
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        today_logs = db.query(ConsultationLog).filter(
            ConsultationLog.doctor_id == doctor_id,
            ConsultationLog.start_time >= today_start,
            ConsultationLog.start_time <= today_end,
            ConsultationLog.end_time.isnot(None)
        ).order_by(ConsultationLog.start_time.asc()).all()

        hourly_counts = {}
        for log in today_logs:
            hour = log.start_time.hour
            hourly_counts[hour] = hourly_counts.get(hour, 0) + 1

        if not hourly_counts:
            return {
                "doctor_id": doctor_id,
                "hours": [],
                "consultations": [],
                "total_consultations": 0,
                "last_updated": datetime.now().isoformat()
            }

        sorted_hours = sorted(hourly_counts.keys())

        def format_hour(hour_value: int):
            hour_12 = hour_value % 12 or 12
            suffix = "AM" if hour_value < 12 else "PM"
            return f"{hour_12}{suffix}"

        return {
            "doctor_id": doctor_id,
            "hours": [format_hour(hour) for hour in sorted_hours],
            "consultations": [hourly_counts[hour] for hour in sorted_hours],
            "total_consultations": sum(hourly_counts.values()),
            "last_updated": datetime.now().isoformat()
        }

    @staticmethod
    def get_last_activity(db: Session, doctor_id: int):
        """Get time since doctor's last action."""
        # Most recent consultation log (started or ended)
        last_log = db.query(ConsultationLog).filter(
            ConsultationLog.doctor_id == doctor_id
        ).order_by(ConsultationLog.start_time.desc()).first()

        last_ts = None
        if last_log:
            last_ts = last_log.end_time or last_log.start_time

        # Also check check-in/check-out
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doctor:
            for ts in [doctor.last_check_in, doctor.last_check_out]:
                if ts and (last_ts is None or ts > last_ts):
                    last_ts = ts

        if last_ts is None:
            return {"last_activity": "No activity yet", "timestamp": None}

        delta = datetime.now() - last_ts
        total_seconds = int(delta.total_seconds())
        if total_seconds < 60:
            formatted = f"{total_seconds} sec ago"
        elif total_seconds < 3600:
            formatted = f"{total_seconds // 60} min ago"
        else:
            hrs = total_seconds // 3600
            formatted = f"{hrs} hrs ago"

        return {"last_activity": formatted, "timestamp": last_ts.isoformat()}

    @staticmethod
    def get_workload_status(db: Session, doctor_id: int):
        """Determine workload level based on today's consultations."""
        today = date.today()
        today_start = datetime.combine(today, datetime.min.time())
        today_end = datetime.combine(today, datetime.max.time())

        completed_count = db.query(ConsultationLog).filter(
            ConsultationLog.doctor_id == doctor_id,
            ConsultationLog.start_time >= today_start,
            ConsultationLog.start_time <= today_end,
            ConsultationLog.end_time.isnot(None)
        ).count()

        # Active (in-progress) consultations as queue indicator
        active_count = db.query(ConsultationLog).filter(
            ConsultationLog.doctor_id == doctor_id,
            ConsultationLog.start_time >= today_start,
            ConsultationLog.end_time.is_(None)
        ).count()

        total_load = completed_count + (active_count * 2)

        if total_load >= 15:
            status, color = "High", "red"
        elif total_load >= 6:
            status, color = "Moderate", "orange"
        else:
            status, color = "Low", "green"

        return {
            "status": status,
            "color": color,
            "completed_today": completed_count,
            "active_now": active_count
        }

    @staticmethod
    def get_stats(db: Session, doctor_id: int):
        """Get doctor's last update time and total action count."""
        # Total actions = all consultation logs for this doctor (start + complete each count)
        all_logs = db.query(ConsultationLog).filter(
            ConsultationLog.doctor_id == doctor_id
        ).all()

        total_actions = 0
        last_update_ts = None
        for log in all_logs:
            total_actions += 1  # start
            if log.end_time:
                total_actions += 1  # complete
            # Track latest timestamp
            ts = log.end_time or log.start_time
            if last_update_ts is None or ts > last_update_ts:
                last_update_ts = ts

        # Also count check-in/out as actions
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doctor:
            if doctor.last_check_in:
                total_actions += 1
                if last_update_ts is None or doctor.last_check_in > last_update_ts:
                    last_update_ts = doctor.last_check_in
            if doctor.last_check_out:
                total_actions += 1
                if last_update_ts is None or doctor.last_check_out > last_update_ts:
                    last_update_ts = doctor.last_check_out

        last_update = last_update_ts.strftime("%H:%M") if last_update_ts else "--:--"

        return {
            "last_update": last_update,
            "total_actions": total_actions
        }

    @staticmethod
    def get_activity_history(db: Session, doctor_id: int):
        """Get full activity history for a doctor, newest first."""
        activities = []

        # Consultation logs
        logs = db.query(ConsultationLog).filter(
            ConsultationLog.doctor_id == doctor_id
        ).order_by(ConsultationLog.start_time.desc()).all()

        for log in logs:
            # Completed consultation
            if log.end_time:
                activities.append({
                    "time": log.end_time.strftime("%H:%M"),
                    "action": f"Patient {log.patient_id}: Consultation Completed",
                    "date": f"{log.end_time.day} {log.end_time.strftime('%b')}",
                    "sort_ts": log.end_time
                })
            # Consultation started
            activities.append({
                "time": log.start_time.strftime("%H:%M"),
                "action": f"Patient {log.patient_id}: Consultation Started",
                "date": f"{log.start_time.day} {log.start_time.strftime('%b')}",
                "sort_ts": log.start_time
            })

        # Check-in / Check-out events
        doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
        if doctor:
            if doctor.last_check_in:
                activities.append({
                    "time": doctor.last_check_in.strftime("%H:%M"),
                    "action": "Doctor Checked In",
                    "date": f"{doctor.last_check_in.day} {doctor.last_check_in.strftime('%b')}",
                    "sort_ts": doctor.last_check_in
                })
            if doctor.last_check_out:
                activities.append({
                    "time": doctor.last_check_out.strftime("%H:%M"),
                    "action": "Doctor Checked Out",
                    "date": f"{doctor.last_check_out.day} {doctor.last_check_out.strftime('%b')}",
                    "sort_ts": doctor.last_check_out
                })

        # Sort newest first
        activities.sort(key=lambda x: x["sort_ts"], reverse=True)

        # Remove sort_ts before returning
        for a in activities:
            del a["sort_ts"]

        return {"activities": activities}
