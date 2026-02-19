"""
PatientPath AI - Zones Router
=============================
API endpoints for zone management.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from schemas.zone import (
    ZoneCreate, ZoneUpdate, ZoneResponse, 
    ZoneListResponse, ZoneOccupancyUpdate, ZoneSummary
)
from schemas.common import SuccessResponse
from services.zone_service import ZoneService
from services.alert_service import AlertService
from utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/zones", tags=["Zones"])


@router.get(
    "",
    response_model=ZoneListResponse,
    summary="List All Zones",
    description="Get all zones with their current status."
)
async def list_zones(
    active_only: bool = Query(True, description="Only return active zones"),
    zone_type: Optional[str] = Query(None, description="Filter by zone type"),
    db: Session = Depends(get_db)
):
    """
    Get list of all zones.
    
    Args:
        active_only: Only return active zones
        zone_type: Optional zone type filter
        
    Returns:
        List of zones with occupancy data
        
    Example Response:
    ```json
    {
        "zones": [...],
        "total": 10,
        "total_capacity": 300,
        "total_occupancy": 120,
        "overall_percentage": 40.0
    }
    ```
    """
    zone_service = ZoneService(db)
    zones = zone_service.get_all_zones(
        active_only=active_only,
        zone_type=zone_type
    )
    
    total_capacity = sum(z.capacity_limit for z in zones)
    total_occupancy = sum(z.current_occupancy for z in zones)
    
    return ZoneListResponse(
        zones=[
            ZoneResponse(
                zone_id=z.zone_id,
                zone_name=z.zone_name,
                display_name=z.display_name,
                description=z.description,
                capacity_limit=z.capacity_limit,
                current_occupancy=z.current_occupancy,
                available_capacity=z.available_capacity,
                occupancy_percentage=z.occupancy_percentage,
                status=z.status,
                zone_type=z.zone_type,
                floor_number=z.floor_number,
                building=z.building,
                is_active=z.is_active,
                is_restricted=z.is_restricted,
                is_at_capacity=z.is_at_capacity,
                warning_threshold=z.warning_threshold,
                critical_threshold=z.critical_threshold,
                created_at=z.created_at,
                updated_at=z.updated_at
            )
            for z in zones
        ],
        total=len(zones),
        total_capacity=total_capacity,
        total_occupancy=total_occupancy,
        overall_percentage=round(
            (total_occupancy / total_capacity * 100) if total_capacity > 0 else 0,
            2
        )
    )


@router.post(
    "",
    response_model=ZoneResponse,
    summary="Create Zone",
    description="Create a new zone in the facility."
)
async def create_zone(
    data: ZoneCreate,
    db: Session = Depends(get_db)
):
    """
    Create a new zone.
    
    Example Request:
    ```json
    {
        "zone_name": "waiting_area_1",
        "display_name": "Main Waiting Area",
        "description": "Primary waiting area near entrance",
        "capacity_limit": 30,
        "zone_type": "waiting",
        "floor_number": 1,
        "building": "Main Building"
    }
    ```
    """
    zone_service = ZoneService(db)
    
    # Check if zone already exists
    existing = zone_service.get_zone_by_name(data.zone_name)
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Zone '{data.zone_name}' already exists"
        )
    
    zone = zone_service.create_zone(data)
    
    logger.info(f"Created zone: {zone.zone_name}")
    
    return ZoneResponse(
        zone_id=zone.zone_id,
        zone_name=zone.zone_name,
        display_name=zone.display_name,
        description=zone.description,
        capacity_limit=zone.capacity_limit,
        current_occupancy=zone.current_occupancy,
        available_capacity=zone.available_capacity,
        occupancy_percentage=zone.occupancy_percentage,
        status=zone.status,
        zone_type=zone.zone_type,
        floor_number=zone.floor_number,
        building=zone.building,
        is_active=zone.is_active,
        is_restricted=zone.is_restricted,
        is_at_capacity=zone.is_at_capacity,
        warning_threshold=zone.warning_threshold,
        critical_threshold=zone.critical_threshold,
        created_at=zone.created_at,
        updated_at=zone.updated_at
    )


@router.post(
    "/update",
    response_model=ZoneResponse,
    summary="Update Zone",
    description="Update zone information or occupancy."
)
async def update_zone(
    data: ZoneOccupancyUpdate,
    db: Session = Depends(get_db)
):
    """
    Update zone occupancy from CV module.
    
    This is the primary endpoint for CV module to report
    real-time people counts.
    
    Example Request:
    ```json
    {
        "zone_name": "waiting_area_1",
        "people_count": 18,
        "confidence_score": 0.94,
        "frame_id": "frame_12345",
        "entry_count": 3,
        "exit_count": 1
    }
    ```
    """
    zone_service = ZoneService(db)
    alert_service = AlertService(db)
    
    zone = zone_service.update_occupancy(data)
    
    if not zone:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{data.zone_name}' not found"
        )
    
    # Log occupancy update
    from services.occupancy_svc import OccupancyService
    from schemas.occupancy import OccupancyUpdate
    
    occupancy_service = OccupancyService(db)
    occupancy_service.log_occupancy(OccupancyUpdate(
        zone_name=data.zone_name,
        people_count=data.people_count,
        confidence_score=data.confidence_score,
        entry_count=data.entry_count,
        exit_count=data.exit_count,
        frame_id=data.frame_id
    ))
    
    # Check for alerts
    alert_service.check_zone_thresholds(zone)
    
    return ZoneResponse(
        zone_id=zone.zone_id,
        zone_name=zone.zone_name,
        display_name=zone.display_name,
        description=zone.description,
        capacity_limit=zone.capacity_limit,
        current_occupancy=zone.current_occupancy,
        available_capacity=zone.available_capacity,
        occupancy_percentage=zone.occupancy_percentage,
        status=zone.status,
        zone_type=zone.zone_type,
        floor_number=zone.floor_number,
        building=zone.building,
        is_active=zone.is_active,
        is_restricted=zone.is_restricted,
        is_at_capacity=zone.is_at_capacity,
        warning_threshold=zone.warning_threshold,
        critical_threshold=zone.critical_threshold,
        created_at=zone.created_at,
        updated_at=zone.updated_at
    )


@router.put(
    "/{zone_name}",
    response_model=ZoneResponse,
    summary="Update Zone Settings",
    description="Update zone configuration and settings."
)
async def update_zone_settings(
    zone_name: str,
    data: ZoneUpdate,
    db: Session = Depends(get_db)
):
    """
    Update zone settings (capacity, thresholds, etc.).
    
    Example Request:
    ```json
    {
        "capacity_limit": 35,
        "warning_threshold": 0.75,
        "critical_threshold": 0.90
    }
    ```
    """
    zone_service = ZoneService(db)
    zone = zone_service.update_zone(zone_name, data)
    
    if not zone:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_name}' not found"
        )
    
    return ZoneResponse(
        zone_id=zone.zone_id,
        zone_name=zone.zone_name,
        display_name=zone.display_name,
        description=zone.description,
        capacity_limit=zone.capacity_limit,
        current_occupancy=zone.current_occupancy,
        available_capacity=zone.available_capacity,
        occupancy_percentage=zone.occupancy_percentage,
        status=zone.status,
        zone_type=zone.zone_type,
        floor_number=zone.floor_number,
        building=zone.building,
        is_active=zone.is_active,
        is_restricted=zone.is_restricted,
        is_at_capacity=zone.is_at_capacity,
        warning_threshold=zone.warning_threshold,
        critical_threshold=zone.critical_threshold,
        created_at=zone.created_at,
        updated_at=zone.updated_at
    )


@router.get(
    "/{zone_name}",
    response_model=ZoneResponse,
    summary="Get Zone Details",
    description="Get detailed information about a specific zone."
)
async def get_zone(
    zone_name: str,
    db: Session = Depends(get_db)
):
    """Get zone details by name."""
    zone_service = ZoneService(db)
    zone = zone_service.get_zone_by_name(zone_name)
    
    if not zone:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_name}' not found"
        )
    
    return ZoneResponse(
        zone_id=zone.zone_id,
        zone_name=zone.zone_name,
        display_name=zone.display_name,
        description=zone.description,
        capacity_limit=zone.capacity_limit,
        current_occupancy=zone.current_occupancy,
        available_capacity=zone.available_capacity,
        occupancy_percentage=zone.occupancy_percentage,
        status=zone.status,
        zone_type=zone.zone_type,
        floor_number=zone.floor_number,
        building=zone.building,
        is_active=zone.is_active,
        is_restricted=zone.is_restricted,
        is_at_capacity=zone.is_at_capacity,
        warning_threshold=zone.warning_threshold,
        critical_threshold=zone.critical_threshold,
        created_at=zone.created_at,
        updated_at=zone.updated_at
    )


@router.get(
    "/summary/all",
    response_model=List[ZoneSummary],
    summary="Get Zone Summaries",
    description="Get simplified zone summaries for dashboard widgets."
)
async def get_zone_summaries(
    db: Session = Depends(get_db)
):
    """Get simplified zone summaries."""
    zone_service = ZoneService(db)
    zones = zone_service.get_all_zones(active_only=True)
    
    return [
        ZoneSummary(
            zone_name=z.zone_name,
            display_name=z.display_name or z.zone_name,
            current_occupancy=z.current_occupancy,
            capacity_limit=z.capacity_limit,
            occupancy_percentage=z.occupancy_percentage,
            status=z.status
        )
        for z in zones
    ]


@router.get(
    "/types/list",
    response_model=List[str],
    summary="Get Zone Types",
    description="Get list of unique zone types."
)
async def get_zone_types(
    db: Session = Depends(get_db)
):
    """Get list of zone types."""
    zone_service = ZoneService(db)
    return zone_service.get_zone_types()


@router.delete(
    "/{zone_name}",
    response_model=SuccessResponse,
    summary="Delete Zone",
    description="Deactivate a zone (soft delete)."
)
async def delete_zone(
    zone_name: str,
    db: Session = Depends(get_db)
):
    """Deactivate a zone."""
    zone_service = ZoneService(db)
    success = zone_service.delete_zone(zone_name)
    
    if not success:
        raise HTTPException(
            status_code=404,
            detail=f"Zone '{zone_name}' not found"
        )
    
    return SuccessResponse(
        message=f"Zone '{zone_name}' deactivated successfully"
    )
