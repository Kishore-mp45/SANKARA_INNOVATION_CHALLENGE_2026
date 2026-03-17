"""
PatientPath AI - Export Router
==============================
API endpoints for CSV data export.
"""

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import io
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from services.analytics_service import AnalyticsService
from utils.logger import get_logger
from auth import require_role

logger = get_logger(__name__)
router = APIRouter(prefix="/export", tags=["Export"])

# Shared auth dependency — all export endpoints require admin or staff role
_export_auth = Depends(require_role("admin", "staff"))


@router.get(
    "/occupancy/csv",
    summary="Export Occupancy Data",
    description="Export occupancy logs to CSV file."
)
async def export_occupancy_csv(
    zone_name: Optional[str] = Query(None, description="Filter by zone"),
    start_time: Optional[datetime] = Query(None, description="Start time"),
    end_time: Optional[datetime] = Query(None, description="End time"),
    hours: int = Query(24, ge=1, le=720, description="Hours to export (if no start_time)"),
    db: Session = Depends(get_db),
    _user: dict = _export_auth
):
    """
    Export occupancy data to CSV.
    
    Returns:
        CSV file download
    """
    analytics_service = AnalyticsService(db)
    
    # Set default time range
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(hours=hours)
    
    csv_data = analytics_service.export_occupancy_csv(
        zone_name=zone_name,
        start_time=start_time,
        end_time=end_time
    )
    
    # Generate filename
    filename = f"occupancy_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    if zone_name:
        filename = f"occupancy_{zone_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get(
    "/patients/csv",
    summary="Export Patient Data",
    description="Export patient records to CSV file."
)
async def export_patients_csv(
    include_exited: bool = Query(True, description="Include exited patients"),
    start_time: Optional[datetime] = Query(None, description="Entry time start"),
    end_time: Optional[datetime] = Query(None, description="Entry time end"),
    db: Session = Depends(get_db),
    _user: dict = _export_auth
):
    """
    Export patient data to CSV.
    
    Returns:
        CSV file download
    """
    analytics_service = AnalyticsService(db)
    
    csv_data = analytics_service.export_patients_csv(
        include_exited=include_exited,
        start_time=start_time,
        end_time=end_time
    )
    
    filename = f"patients_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get(
    "/metrics/csv",
    summary="Export Metrics Data",
    description="Export aggregated metrics to CSV file."
)
async def export_metrics_csv(
    metric_type: str = Query("hourly", description="Metric type"),
    zone_name: Optional[str] = Query(None, description="Filter by zone"),
    start_time: Optional[datetime] = Query(None, description="Start time"),
    end_time: Optional[datetime] = Query(None, description="End time"),
    db: Session = Depends(get_db),
    _user: dict = _export_auth
):
    """
    Export metrics data to CSV.
    
    Returns:
        CSV file download
    """
    analytics_service = AnalyticsService(db)
    
    csv_data = analytics_service.export_metrics_csv(
        metric_type=metric_type,
        zone_name=zone_name,
        start_time=start_time,
        end_time=end_time
    )
    
    filename = f"metrics_{metric_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )
