"""
PatientPath AI - Patients Router
================================
API endpoints for patient management and tracking.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from models.patient import Patient, PatientStatus as ModelPatientStatus
from schemas.patient import (
    PatientEnter, PatientExit, PatientResponse, 
    PatientListResponse, PatientUpdate, PatientStatus,
    PatientMovement, PatientStageUpdate, PatientCreate
)
from schemas.common import SuccessResponse, ErrorResponse
from services import (
    PatientService,
    ZoneService,
    OccupancyService,
    AlertService,
    ActivityService
)
from services.prediction_service import PredictionService
from schemas.occupancy import OccupancyUpdate
from utils.logger import get_logger
from utils.helpers import calculate_pagination

logger = get_logger(__name__)
router = APIRouter(prefix="/patient", tags=["Patients"])


@router.post(
    "/enter",
    response_model=PatientResponse,
    summary="Register Patient Entry",
    description="Register a new patient entering the facility."
)
async def patient_enter(
    data: PatientEnter,
    db: Session = Depends(get_db)
):
    """
    Register a patient entry event.
    
    This endpoint is called when:
    - CV module detects a new person entering
    - Manual patient registration
    
    Args:
        data: Patient entry information
        
    Returns:
        Created patient record
        
    Example Request:
    ```json
    {
        "name": "Patient A",
        "tracking_id": "CV-12345",
        "zone_name": "entrance",
        "entry_time": "2024-01-15T10:30:00Z"
    }
    ```
    """
    # Verify zone exists
    zone_service = ZoneService(db)
    zone = zone_service.get_zone_by_name(data.zone_name)
    if not zone:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{data.zone_name}' not found"
        )

    # Check if patient already exists
    existing = PatientService.get_by_tracking_id(db, data.tracking_id)
    if existing:
        # If exists, update entry time or just return?
        # Let's return existing to be safe given current context
        logger.info(f"Patient {data.tracking_id} already exists, returning existing record")
        return existing

    # Create patient
    patient_create = PatientCreate(
        name=data.name,
        tracking_id=data.tracking_id,
        status=PatientStatus.ENTERED,
        current_zone=data.zone_name
    )
    patient = PatientService.create(db, patient_create)
    
    # Update zone occupancy
    if zone.current_occupancy < zone.capacity_limit * 2:
        zone.current_occupancy += 1
    db.commit()
    
    # Check for capacity alerts
    alert_service = AlertService(db)
    alert_service.check_zone_thresholds(zone)
    
    logger.info(f"Patient entered: ID={patient.id}, Zone={data.zone_name}")

    # Log to Activity Service
    ActivityService.add_log(
        action="Patient Entry",
        details=f"{patient.name} ({patient.tracking_id}) entered at {data.zone_name}",
        severity="success",
        role="system",
        user_id="System"
    )

    return PatientResponse(
        id=patient.id,
        name=patient.name,
        mobile=patient.mobile,
        tracking_id=patient.tracking_id,
        entry_time=patient.entry_time,
        exit_time=patient.exit_time,
        status=patient.status,
        current_zone=patient.current_zone,
        is_active=patient.is_active,
        dwell_time_minutes=patient.dwell_time_minutes,
        created_at=patient.created_at,
        updated_at=patient.updated_at
    )


@router.post(
    "/exit",
    response_model=PatientResponse,
    summary="Register Patient Exit",
    description="Register a patient leaving the facility."
)
async def patient_exit(
    data: PatientExit,
    db: Session = Depends(get_db)
):
    """
    Register a patient exit event.
    
    This endpoint is called when:
    - CV module detects a person exiting
    - Manual checkout
    
    Args:
        data: Patient exit information
        
    Returns:
        Updated patient record
        
    Example Request:
    ```json
    {
        "patient_id": 1,
        "tracking_id": "CV-12345",
        "exit_time": "2024-01-15T11:45:00Z",
        "exit_zone": "exit"
    }
    ```
    """
    patient_service = PatientService(db)
    zone_service = ZoneService(db)
    
    # Register exit
    patient = patient_service.patient_exit(data)
    
    if not patient:
        raise HTTPException(
            status_code=404,
            detail="Patient not found"
        )
    
    # Update zone occupancy
    if patient.current_zone:
        zone = zone_service.get_zone_by_name(patient.current_zone)
        if zone and zone.current_occupancy > 0:
            zone.current_occupancy -= 1
            db.commit()
            
            # Check if alerts can be resolved
            alert_service = AlertService(db)
            alert_service.check_zone_thresholds(zone)
    
    logger.info(f"Patient exited: ID={patient.id}, Dwell={patient.dwell_time_minutes}min")

    # Log to Activity Service
    ActivityService.add_log(
        action="Patient Discharged",
        details=f"{patient.name} ({patient.tracking_id}) exited — dwell time: {patient.dwell_time_minutes}min",
        severity="info",
        role="system",
        user_id="System"
    )

    return PatientResponse(
        id=patient.id,
        name=patient.name,
        mobile=patient.mobile,
        tracking_id=patient.tracking_id,
        entry_time=patient.entry_time,
        exit_time=patient.exit_time,
        status=patient.status,
        current_zone=patient.current_zone,
        is_active=patient.is_active,
        dwell_time_minutes=patient.dwell_time_minutes,
        created_at=patient.created_at,
        updated_at=patient.updated_at
    )


@router.get(
    "/list",
    response_model=PatientListResponse,
    summary="List Patients",
    description="Get paginated list of patients with optional filters."
)
async def list_patients(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter by status"),
    zone: Optional[str] = Query(None, description="Filter by zone"),
    active_only: bool = Query(False, description="Only show active patients"),
    db: Session = Depends(get_db)
):
    """
    Get list of patients with pagination and filters.
    
    Args:
        page: Page number (1-indexed)
        page_size: Number of items per page
        status: Optional status filter
        zone: Optional zone filter
        active_only: Only return patients currently in facility
        
    Returns:
        Paginated patient list
        
    Example Response:
    ```json
    {
        "patients": [...],
        "total": 150,
        "active_count": 42,
        "page": 1,
        "page_size": 50,
        "total_pages": 3
    }
    ```
    """
    # Build query
    query = db.query(Patient)
    
    # Apply filters
    if status:
        try:
            status_enum = PatientStatus(status)
            query = query.filter(Patient.status == status_enum)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status: {status}"
            )
    
    if zone:
        query = query.filter(Patient.current_zone == zone)
    
    if active_only:
        query = query.filter(Patient.status != PatientStatus.EXITED)
    
    # Get total count
    total = query.count()
    
    # Get active count
    active_count = db.query(Patient).filter(Patient.status != PatientStatus.EXITED).count()
    
    # Pagination
    offset, _, total_pages = calculate_pagination(total, page, page_size)
    patients = query.offset(offset).limit(page_size).all()
    
    return PatientListResponse(
        patients=[
            PatientResponse(
                id=p.id,
                name=p.name,
                mobile=p.mobile,
                tracking_id=p.tracking_id,
                entry_time=p.entry_time,
                exit_time=p.exit_time,
                status=p.status,
                current_zone=p.current_zone,
                is_active=p.is_active,
                dwell_time_minutes=p.dwell_time_minutes,
                created_at=p.created_at,
                updated_at=p.updated_at
            )
            for p in patients
        ],
        total=total,
        active_count=active_count,
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get(
    "/predicted-wait-time/{tracking_id}",
    summary="Get Predicted Wait Time for Patient",
    description="Returns AI-predicted average waiting time for the patient's current department."
)
async def get_predicted_wait_time(
    tracking_id: str,
    db: Session = Depends(get_db)
):
    """
    Get predicted wait time for a specific patient based on their current department.
    Uses the trained XGBoost waiting_model.pkl.
    """
    patient = PatientService.get_by_tracking_id(db, tracking_id)

    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {tracking_id} not found")

    current_zone = patient.current_zone
    if not current_zone:
        return {
            "tracking_id": tracking_id,
            "department": None,
            "predicted_minutes": None,
            "formatted": "--",
            "available": False,
            "message": "Patient has no current department assigned."
        }

    result = PredictionService.predict_department_wait(db, current_zone)
    result["tracking_id"] = tracking_id
    return result


@router.get(
    "/{patient_id}",
    response_model=PatientResponse,
    summary="Get Patient Details",
    description="Get detailed information about a specific patient."
)
async def get_patient(
    patient_id: int,
    db: Session = Depends(get_db)
):
    """Get patient by ID."""
    patient_service = PatientService(db)
    patient = patient_service.get_patient_by_id(patient_id)
    
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    return PatientResponse(
        id=patient.id,
        name=patient.name,
        mobile=patient.mobile,
        tracking_id=patient.tracking_id,
        entry_time=patient.entry_time,
        exit_time=patient.exit_time,
        status=patient.status,
        current_zone=patient.current_zone,
        is_active=patient.is_active,
        dwell_time_minutes=patient.dwell_time_minutes,
        created_at=patient.created_at,
        updated_at=patient.updated_at
    )


@router.get(
    "/tracking/{tracking_id}",
    summary="Get Patient by Tracking ID",
    description="Get detailed information about a specific patient using their tracking ID."
)
async def get_patient_by_tracking_id(
    tracking_id: str,
    db: Session = Depends(get_db)
):
    """Get patient by Tracking ID."""
    try:
        patient = PatientService.get_by_tracking_id(db, tracking_id)
        
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {tracking_id} not found")
        
        # Build response with consultation history
        result = patient.to_dict()

        # Include consultation logs for timeline display
        from models.doctor import ConsultationLog, Doctor
        logs = db.query(ConsultationLog).filter(
            ConsultationLog.patient_id == tracking_id
        ).order_by(ConsultationLog.start_time.desc()).limit(10).all()

        consultation_history = []
        for log in logs:
            doctor = db.query(Doctor).filter(Doctor.id == log.doctor_id).first()
            doctor_name = doctor.name if doctor else "Doctor"
            entry = {
                "start_time": log.start_time.isoformat() if log.start_time else None,
                "end_time": log.end_time.isoformat() if log.end_time else None,
                "doctor_name": doctor_name,
                "notes": log.notes
            }
            consultation_history.append(entry)

        result["consultation_history"] = consultation_history
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching patient {tracking_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")


@router.post(
    "/movement",
    response_model=PatientResponse,
    summary="Record Patient Movement",
    description="Record patient movement between zones (from CV module)."
)
async def record_movement(
    data: PatientMovement,
    db: Session = Depends(get_db)
):
    """
    Record patient zone movement from CV tracking.
    
    Example Request:
    ```json
    {
        "tracking_id": "CV-12345",
        "from_zone": "entrance",
        "to_zone": "waiting_area",
        "timestamp": "2024-01-15T10:35:00Z",
        "confidence": 0.95
    }
    ```
    """
    patient_service = PatientService(db)
    zone_service = ZoneService(db)
    
    # Verify destination zone exists
    to_zone = zone_service.get_zone_by_name(data.to_zone)
    if not to_zone:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{data.to_zone}' not found"
        )
    
    # Update patient zone
    patient = patient_service.update_patient_zone(
        tracking_id=data.tracking_id,
        new_zone=data.to_zone
    )
    
    if not patient:
        raise HTTPException(
            status_code=404,
            detail=f"Patient with tracking_id '{data.tracking_id}' not found"
        )
    
    # Update zone occupancies
    if data.from_zone:
        from_zone = zone_service.get_zone_by_name(data.from_zone)
        if from_zone and from_zone.current_occupancy > 0:
            from_zone.current_occupancy -= 1
    
    to_zone.current_occupancy += 1
    db.commit()
    
    # Check alerts
    alert_service = AlertService(db)
    alert_service.check_zone_thresholds(to_zone)

    # Log to Activity Service
    ActivityService.add_log(
        action=f"Movement Detected: {data.to_zone}",
        details=f"Patient {patient.tracking_id} moved to {data.to_zone} (Confidence: {getattr(data, 'confidence', 'N/A')})",
        severity="info",
        role="System",
        user_id="CV-Module"
    )
    
    return PatientResponse(
        id=patient.id,
        name=patient.name,
        mobile=patient.mobile,
        tracking_id=patient.tracking_id,
        entry_time=patient.entry_time,
        exit_time=patient.exit_time,
        status=patient.status,
        current_zone=patient.current_zone,
        is_active=patient.is_active,
        dwell_time_minutes=patient.dwell_time_minutes,
        created_at=patient.created_at,
        updated_at=patient.updated_at
    )


@router.get(
    "/zone/{zone_name}",
    response_model=List[PatientResponse],
    summary="Get Patients in Zone",
    description="Get all active patients in a specific zone."
)
async def get_patients_by_zone(
    zone_name: str,
    db: Session = Depends(get_db)
):
    """Get all active patients in a specific zone."""
    patient_service = PatientService(db)
    patients = patient_service.get_patients_by_zone(zone_name)
    
    return [
        PatientResponse(
            id=p.id,
            name=p.name,
            mobile=p.mobile,
            tracking_id=p.tracking_id,
            entry_time=p.entry_time,
            exit_time=p.exit_time,
            status=p.status,
            current_zone=p.current_zone,
            is_active=p.is_active,
            dwell_time_minutes=p.dwell_time_minutes,
            created_at=p.created_at,
            updated_at=p.updated_at
        )
        for p in patients
    ]


@router.post(
    "/update-stage",
    response_model=SuccessResponse,
    summary="Update Patient Stage",
    description="Manually update patient stage/zone from staff panel."
)
async def update_patient_stage(
    data: PatientStageUpdate,
    db: Session = Depends(get_db)
):
    """
    Manually update patient stage.
    
    This endpoint allows staff to move patients between departments and record actions.
    """
    try:
        with open("debug_log.txt", "a") as f:
            f.write(f"DEBUG: Endpoint called with {data}\n")
    except:
        pass

    try:
        # Use centralized service logic covering logging, alerts, and zone updates
        patient = PatientService.update_patient_stage(
            db=db,
            tracking_id=data.tracking_id,
            department=data.department,
            action=data.action,
            next_department=data.next_department,
            staff_id=data.staff_id,
            name=data.name,
            mobile=data.mobile
        )
        
        return SuccessResponse(
            success=True,
            message=f"Patient {patient.tracking_id} updated successfully. Action: {patient.last_action}"
        )
    except HTTPException:
        raise
    except Exception as e:
        with open("debug_log_error.txt", "w") as f:
            f.write(f"CRITICAL ERROR: {e}\n")
            import traceback
            traceback.print_exc(file=f)
        logger.error(f"Critical error in update_patient_stage: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")
