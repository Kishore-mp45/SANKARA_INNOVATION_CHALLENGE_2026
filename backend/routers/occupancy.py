"""
PatientPath AI - Occupancy Router
=================================
API endpoints for occupancy tracking and logging.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timedelta
import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from schemas.occupancy import (
    OccupancyUpdate, OccupancyBatchUpdate, OccupancyLogResponse,
    OccupancyCurrentResponse, OccupancyHistoryResponse
)
from schemas.common import SuccessResponse
from services.occupancy_svc import OccupancyService
from services.zone_service import ZoneService
from services.alert_service import AlertService
from utils.logger import get_logger
from utils.helpers import calculate_pagination

logger = get_logger(__name__)
router = APIRouter(prefix="/occupancy", tags=["Occupancy"])


@router.post(
    "/update",
    response_model=OccupancyLogResponse,
    summary="Update Occupancy",
    description="Receive occupancy update from CV module."
)
async def update_occupancy(
    data: OccupancyUpdate,
    db: Session = Depends(get_db)
):
    """
    Update occupancy from CV module detection.
    
    This is the primary endpoint for real-time CV module integration.
    Call this endpoint with each frame's detection results.
    
    Args:
        data: Occupancy detection data
        
    Returns:
        Created occupancy log
        
    Example Request:
    ```json
    {
        "zone_name": "entrance",
        "people_count": 12,
        "timestamp": "2024-01-15T10:30:00Z",
        "confidence_score": 0.95,
        "entry_count": 5,
        "exit_count": 3,
        "frame_id": "frame_00123",
        "source": "cv_module"
    }
    ```
    """
    import inspect
    try:
        print(f"DEBUG: Service imported from: {inspect.getfile(OccupancyService)}")
        print(f"DEBUG: OccupancyService class: {OccupancyService}")
        print(f"DEBUG: OccupancyService init: {OccupancyService.__init__}")
    except Exception as e:
        print(f"DEBUG: Inspection failed: {e}")
        
    occupancy_service = OccupancyService(db)
    zone_service = ZoneService(db)
    alert_service = AlertService(db)
    
    # Verify zone exists
    zone = zone_service.get_zone_by_name(data.zone_name)
    if not zone:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{data.zone_name}' not found"
        )
    
    # Log occupancy
    log = occupancy_service.log_occupancy(data)
    
    # Check for threshold alerts
    alert_service.check_zone_thresholds(zone)

    # Broadcast update via WebSocket
    try:
        from routers.websocket import broadcast_occupancy_update
        await broadcast_occupancy_update({
            "zone": log.zone_name,
            "count": log.people_count,
            "timestamp": log.timestamp.isoformat()
        })
    except Exception as e:
        logger.error(f"Failed to broadcast update: {e}")
    
    return OccupancyLogResponse(
        id=log.id,
        timestamp=log.timestamp,
        people_count=log.people_count,
        previous_count=log.previous_count,
        delta=log.delta,
        zone_name=log.zone_name,
        entry_count=log.entry_count,
        exit_count=log.exit_count,
        net_flow=log.net_flow,
        confidence_score=log.confidence_score,
        source=log.source
    )


@router.post(
    "/batch",
    response_model=List[OccupancyLogResponse],
    summary="Batch Update Occupancy",
    description="Update occupancy for multiple zones at once."
)
async def batch_update_occupancy(
    data: OccupancyBatchUpdate,
    db: Session = Depends(get_db)
):
    """
    Batch update occupancy for multiple zones.
    
    Useful for CV systems monitoring multiple zones simultaneously.
    
    Example Request:
    ```json
    {
        "updates": [
            {"zone_name": "entrance", "people_count": 12},
            {"zone_name": "waiting_area", "people_count": 25}
        ],
        "batch_timestamp": "2024-01-15T10:30:00Z",
        "batch_id": "batch_001"
    }
    ```
    """
    occupancy_service = OccupancyService(db)
    logs = occupancy_service.log_batch_occupancy(data)
    
    return [
        OccupancyLogResponse(
            id=log.id,
            timestamp=log.timestamp,
            people_count=log.people_count,
            previous_count=log.previous_count,
            delta=log.delta,
            zone_name=log.zone_name,
            entry_count=log.entry_count,
            exit_count=log.exit_count,
            net_flow=log.net_flow,
            confidence_score=log.confidence_score,
            source=log.source
        )
        for log in logs
    ]


@router.get(
    "/current",
    response_model=OccupancyCurrentResponse,
    summary="Get Current Occupancy",
    description="Get current occupancy state across all zones."
)
async def get_current_occupancy(
    db: Session = Depends(get_db)
):
    """
    Get current facility-wide occupancy.
    
    Returns:
        Current occupancy state for all zones
        
    Example Response:
    ```json
    {
        "timestamp": "2024-01-15T10:30:00Z",
        "total_occupancy": 85,
        "total_capacity": 200,
        "overall_percentage": 42.5,
        "zones": [
            {
                "zone_name": "entrance",
                "current_occupancy": 12,
                "capacity_limit": 30,
                "percentage": 40.0,
                "status": "normal"
            }
        ]
    }
    ```
    """
    occupancy_service = OccupancyService(db)
    data = occupancy_service.get_current_occupancy()
    
    return OccupancyCurrentResponse(
        timestamp=datetime.fromisoformat(data["timestamp"]),
        total_occupancy=data["total_occupancy"],
        total_capacity=data["total_capacity"],
        overall_percentage=data["overall_percentage"],
        zones=data["zones"]
    )


@router.get(
    "/history",
    response_model=OccupancyHistoryResponse,
    summary="Get Occupancy History",
    description="Get historical occupancy data with filters."
)
async def get_occupancy_history(
    zone_name: Optional[str] = Query(None, description="Filter by zone"),
    start_time: Optional[datetime] = Query(None, description="Start time"),
    end_time: Optional[datetime] = Query(None, description="End time"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back (if no start_time)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=1000, description="Items per page"),
    db: Session = Depends(get_db)
):
    """
    Get historical occupancy logs.
    
    Args:
        zone_name: Optional zone filter
        start_time: Query start time
        end_time: Query end time
        hours: Hours to look back (if start_time not provided)
        page: Page number
        page_size: Items per page
        
    Returns:
        Historical occupancy data with statistics
    """
    occupancy_service = OccupancyService(db)
    
    # Set default time range
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(hours=hours)
    
    logs, total, statistics = occupancy_service.get_occupancy_history(
        zone_name=zone_name,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size
    )
    
    return OccupancyHistoryResponse(
        zone_name=zone_name,
        start_time=start_time,
        end_time=end_time,
        interval="raw",
        data_points=total,
        logs=[
            OccupancyLogResponse(
                id=log.id,
                timestamp=log.timestamp,
                people_count=log.people_count,
                previous_count=log.previous_count,
                delta=log.delta,
                zone_name=log.zone_name,
                entry_count=log.entry_count,
                exit_count=log.exit_count,
                net_flow=log.net_flow,
                confidence_score=log.confidence_score,
                source=log.source
            )
            for log in logs
        ],
        statistics=statistics
    )


@router.get(
    "/hourly",
    summary="Get Hourly Aggregates",
    description="Get hourly aggregated occupancy data."
)
async def get_hourly_occupancy(
    zone_name: Optional[str] = Query(None, description="Filter by zone"),
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    db: Session = Depends(get_db)
):
    """
    Get hourly aggregated occupancy data.
    
    Returns:
        List of hourly aggregates
    """
    occupancy_service = OccupancyService(db)
    data = occupancy_service.get_hourly_aggregates(
        zone_name=zone_name,
        hours=hours
    )
    
    return {
        "zone_name": zone_name,
        "hours": hours,
        "data": data
    }


@router.get(
    "/trend/{zone_name}",
    summary="Get Zone Trend",
    description="Analyze occupancy trend for a zone."
)
async def get_zone_trend(
    zone_name: str,
    minutes: int = Query(60, ge=5, le=1440, description="Analysis window in minutes"),
    db: Session = Depends(get_db)
):
    """
    Get occupancy trend analysis for a zone.
    
    Returns:
        Trend direction and change rate
    """
    occupancy_service = OccupancyService(db)
    trend = occupancy_service.get_zone_trend(zone_name, minutes)
    
    return trend


@router.get(
    "/latest/{zone_name}",
    response_model=OccupancyLogResponse,
    summary="Get Latest Reading",
    description="Get the most recent occupancy reading for a zone."
)
async def get_latest_occupancy(
    zone_name: str,
    db: Session = Depends(get_db)
):
    """Get latest occupancy log for a zone."""
    occupancy_service = OccupancyService(db)
    log = occupancy_service.get_latest_log(zone_name)

    if not log:
        raise HTTPException(
            status_code=404,
            detail=f"No occupancy data found for zone '{zone_name}'"
        )

    return OccupancyLogResponse(
        id=log.id,
        timestamp=log.timestamp,
        people_count=log.people_count,
        previous_count=log.previous_count,
        delta=log.delta,
        zone_name=log.zone_name,
        entry_count=log.entry_count,
        exit_count=log.exit_count,
        net_flow=log.net_flow,
        confidence_score=log.confidence_score,
        source=log.source
    )


@router.get(
    "/peak-heatmap",
    summary="Get Peak Hour Heatmap Data",
    description="Get real occupancy data grouped by day and hour for heatmap display."
)
async def get_peak_heatmap(
    zone_name: str = Query(..., description="Zone name"),
    range: str = Query("weekly", description="Range: 'weekly' or 'today'"),
    db: Session = Depends(get_db)
):
    """
    Returns occupancy data aggregated by day-of-week and hour.
    Used by the Peak Hour Heatmap chart in the frontend.

    MySQL DAYOFWEEK: 1=Sunday, 2=Monday, ... 7=Saturday.

    For 'today' mode, only hours up to the current hour are returned.
    """
    occupancy_service = OccupancyService(db)
    data, capacity = occupancy_service.get_peak_heatmap_data(zone_name, range)

    return {
        "zone_name": zone_name,
        "range": range,
        "capacity": capacity,
        "current_hour": datetime.now().hour,
        "data": data
    }
