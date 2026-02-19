"""
PatientPath AI - Alerts Router
==============================
API endpoints for alert management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from schemas.alert import (
    AlertCreate, AlertResponse, AlertListResponse,
    AlertAcknowledge, AlertResolve, AlertSeverity, AlertSummary
)
from schemas.common import SuccessResponse
from services.alert_service import AlertService
from utils.logger import get_logger
from utils.helpers import calculate_pagination

logger = get_logger(__name__)
router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post(
    "/create",
    response_model=AlertResponse,
    summary="Create Alert",
    description="Create a new alert manually."
)
async def create_alert(
    data: AlertCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new alert.
    
    Most alerts are generated automatically by the system,
    but this endpoint allows manual alert creation.
    
    Example Request:
    ```json
    {
        "alert_type": "capacity_warning",
        "severity": "warning",
        "message": "Zone 'waiting_area_1' has reached 85% capacity",
        "zone_name": "waiting_area_1",
        "metric_value": "85%",
        "threshold_value": "80%"
    }
    ```
    """
    alert_service = AlertService(db)
    alert = alert_service.create_alert(data)
    
    return AlertResponse(
        alert_id=alert.alert_id,
        timestamp=alert.timestamp,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        details=alert.details,
        zone_name=alert.zone_name,
        patient_id=alert.patient_id,
        metric_value=alert.metric_value,
        threshold_value=alert.threshold_value,
        is_active=alert.is_active,
        acknowledged=alert.acknowledged,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        age_minutes=alert.age_minutes
    )


@router.get(
    "/active",
    response_model=AlertListResponse,
    summary="Get Active Alerts",
    description="Get all currently active alerts."
)
async def get_active_alerts(
    severity: Optional[str] = Query(None, description="Filter by severity"),
    zone_name: Optional[str] = Query(None, description="Filter by zone"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get all active (unresolved) alerts.
    
    Returns:
        List of active alerts with counts
        
    Example Response:
    ```json
    {
        "alerts": [...],
        "total": 25,
        "active_count": 5,
        "critical_count": 1,
        "unacknowledged_count": 3,
        "page": 1,
        "page_size": 50,
        "total_pages": 1
    }
    ```
    """
    alert_service = AlertService(db)
    
    # Parse severity
    severity_enum = None
    if severity:
        try:
            severity_enum = AlertSeverity(severity)
        except ValueError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity: {severity}"
            )
    
    alerts, total = alert_service.get_active_alerts(
        severity=severity_enum,
        zone_name=zone_name,
        page=page,
        page_size=page_size
    )
    
    # Get counts
    summary = alert_service.get_alert_summary()
    
    total_pages, _, _, _ = calculate_pagination(total, page, page_size)
    
    return AlertListResponse(
        alerts=[
            AlertResponse(
                alert_id=a.alert_id,
                timestamp=a.timestamp,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                details=a.details,
                zone_name=a.zone_name,
                patient_id=a.patient_id,
                metric_value=a.metric_value,
                threshold_value=a.threshold_value,
                is_active=a.is_active,
                acknowledged=a.acknowledged,
                acknowledged_by=a.acknowledged_by,
                acknowledged_at=a.acknowledged_at,
                resolved_at=a.resolved_at,
                resolution_notes=a.resolution_notes,
                age_minutes=a.age_minutes
            )
            for a in alerts
        ],
        total=total,
        active_count=summary["total_active"],
        critical_count=summary["critical_count"],
        unacknowledged_count=summary["unacknowledged_count"],
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )


@router.get(
    "/summary",
    response_model=AlertSummary,
    summary="Get Alert Summary",
    description="Get summary of alerts for dashboard."
)
async def get_alert_summary(
    db: Session = Depends(get_db)
):
    """
    Get alert summary for dashboard widgets.
    
    Returns:
        Alert counts and recent alerts
    """
    alert_service = AlertService(db)
    summary = alert_service.get_alert_summary()
    
    return AlertSummary(
        total_active=summary["total_active"],
        critical_count=summary["critical_count"],
        warning_count=summary["warning_count"],
        info_count=summary["info_count"],
        unacknowledged_count=summary["unacknowledged_count"],
        recent_alerts=[
            AlertResponse(**a) for a in summary["recent_alerts"]
        ]
    )


@router.post(
    "/acknowledge",
    response_model=AlertResponse,
    summary="Acknowledge Alert",
    description="Mark an alert as acknowledged."
)
async def acknowledge_alert(
    data: AlertAcknowledge,
    db: Session = Depends(get_db)
):
    """
    Acknowledge an alert.
    
    Example Request:
    ```json
    {
        "alert_id": 1,
        "acknowledged_by": "admin",
        "notes": "Staff notified, monitoring situation"
    }
    ```
    """
    alert_service = AlertService(db)
    alert = alert_service.acknowledge_alert(data)
    
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {data.alert_id} not found"
        )
    
    logger.info(f"Alert {alert.alert_id} acknowledged by {data.acknowledged_by}")
    
    return AlertResponse(
        alert_id=alert.alert_id,
        timestamp=alert.timestamp,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        details=alert.details,
        zone_name=alert.zone_name,
        patient_id=alert.patient_id,
        metric_value=alert.metric_value,
        threshold_value=alert.threshold_value,
        is_active=alert.is_active,
        acknowledged=alert.acknowledged,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        age_minutes=alert.age_minutes
    )


@router.post(
    "/resolve",
    response_model=AlertResponse,
    summary="Resolve Alert",
    description="Mark an alert as resolved."
)
async def resolve_alert(
    data: AlertResolve,
    db: Session = Depends(get_db)
):
    """
    Resolve an alert.
    
    Example Request:
    ```json
    {
        "alert_id": 1,
        "resolution_notes": "Capacity returned to normal levels"
    }
    ```
    """
    alert_service = AlertService(db)
    alert = alert_service.resolve_alert(data)
    
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {data.alert_id} not found"
        )
    
    logger.info(f"Alert {alert.alert_id} resolved")
    
    return AlertResponse(
        alert_id=alert.alert_id,
        timestamp=alert.timestamp,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        details=alert.details,
        zone_name=alert.zone_name,
        patient_id=alert.patient_id,
        metric_value=alert.metric_value,
        threshold_value=alert.threshold_value,
        is_active=alert.is_active,
        acknowledged=alert.acknowledged,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        age_minutes=alert.age_minutes
    )


@router.get(
    "/{alert_id}",
    response_model=AlertResponse,
    summary="Get Alert Details",
    description="Get detailed information about a specific alert."
)
async def get_alert(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """Get alert by ID."""
    alert_service = AlertService(db)
    alert = alert_service.get_alert_by_id(alert_id)
    
    if not alert:
        raise HTTPException(
            status_code=404,
            detail=f"Alert {alert_id} not found"
        )
    
    return AlertResponse(
        alert_id=alert.alert_id,
        timestamp=alert.timestamp,
        alert_type=alert.alert_type,
        severity=alert.severity,
        message=alert.message,
        details=alert.details,
        zone_name=alert.zone_name,
        patient_id=alert.patient_id,
        metric_value=alert.metric_value,
        threshold_value=alert.threshold_value,
        is_active=alert.is_active,
        acknowledged=alert.acknowledged,
        acknowledged_by=alert.acknowledged_by,
        acknowledged_at=alert.acknowledged_at,
        resolved_at=alert.resolved_at,
        resolution_notes=alert.resolution_notes,
        age_minutes=alert.age_minutes
    )


@router.get(
    "",
    response_model=AlertListResponse,
    summary="List All Alerts",
    description="Get all alerts including resolved ones."
)
async def list_alerts(
    include_resolved: bool = Query(False, description="Include resolved alerts"),
    start_time: Optional[datetime] = Query(None, description="Filter from date"),
    end_time: Optional[datetime] = Query(None, description="Filter to date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    db: Session = Depends(get_db)
):
    """Get all alerts with optional filters."""
    alert_service = AlertService(db)
    
    alerts, total = alert_service.get_all_alerts(
        include_resolved=include_resolved,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size
    )
    
    summary = alert_service.get_alert_summary()
    total_pages, _, _, _ = calculate_pagination(total, page, page_size)
    
    return AlertListResponse(
        alerts=[
            AlertResponse(
                alert_id=a.alert_id,
                timestamp=a.timestamp,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                details=a.details,
                zone_name=a.zone_name,
                patient_id=a.patient_id,
                metric_value=a.metric_value,
                threshold_value=a.threshold_value,
                is_active=a.is_active,
                acknowledged=a.acknowledged,
                acknowledged_by=a.acknowledged_by,
                acknowledged_at=a.acknowledged_at,
                resolved_at=a.resolved_at,
                resolution_notes=a.resolution_notes,
                age_minutes=a.age_minutes
            )
            for a in alerts
        ],
        total=total,
        active_count=summary["total_active"],
        critical_count=summary["critical_count"],
        unacknowledged_count=summary["unacknowledged_count"],
        page=page,
        page_size=page_size,
        total_pages=total_pages
    )
