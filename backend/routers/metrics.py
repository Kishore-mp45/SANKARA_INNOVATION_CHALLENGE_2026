"""
PatientPath AI - Metrics Router
===============================
API endpoints for analytics metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db
from schemas.metric import (
    MetricResponse, MetricLiveResponse, MetricHistoryResponse
)
from services.metric_service import MetricService
from services.analytics_service import AnalyticsService
from utils.logger import get_logger
from utils.helpers import calculate_pagination

logger = get_logger(__name__)
router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get(
    "/live",
    response_model=MetricLiveResponse,
    summary="Get Live Metrics",
    description="Get real-time facility metrics for dashboard."
)
async def get_live_metrics(
    db: Session = Depends(get_db)
):
    """
    Get current real-time metrics.
    
    This endpoint provides live dashboard metrics including:
    - Current occupancy and capacity
    - Entry/exit rates
    - Average dwell time
    - Zone status counts
    - Active alerts count
    
    Returns:
        Real-time metrics snapshot
        
    Example Response:
    ```json
    {
        "timestamp": "2024-01-15T10:30:00Z",
        "current_occupancy": 85,
        "current_capacity": 200,
        "occupancy_percentage": 42.5,
        "entry_rate": 15.5,
        "exit_rate": 12.3,
        "net_flow": 7,
        "avg_dwell_time": 32.5,
        "active_patients": 85,
        "zones_at_warning": 2,
        "zones_at_critical": 0,
        "active_alerts": 3
    }
    ```
    """
    metric_service = MetricService(db)
    data = metric_service.get_live_metrics()
    
    return MetricLiveResponse(
        timestamp=datetime.fromisoformat(data["timestamp"]),
        current_occupancy=data["current_occupancy"],
        current_capacity=data["current_capacity"],
        occupancy_percentage=data["occupancy_percentage"],
        entry_rate=data["entry_rate"],
        exit_rate=data["exit_rate"],
        net_flow=data["net_flow"],
        avg_dwell_time=data["avg_dwell_time"],
        active_patients=data["active_patients"],
        zones_at_warning=data["zones_at_warning"],
        zones_at_critical=data["zones_at_critical"],
        active_alerts=data["active_alerts"]
    )


@router.get(
    "/history",
    response_model=MetricHistoryResponse,
    summary="Get Metric History",
    description="Get historical aggregated metrics."
)
async def get_metric_history(
    zone_name: Optional[str] = Query(None, description="Filter by zone (null for facility-wide)"),
    metric_type: str = Query("hourly", description="Metric type (hourly, daily)"),
    start_time: Optional[datetime] = Query(None, description="Start time"),
    end_time: Optional[datetime] = Query(None, description="End time"),
    hours: int = Query(24, ge=1, le=720, description="Hours to look back"),
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """
    Get historical aggregated metrics.
    
    Returns:
        Historical metrics with summary
        
    Example Response:
    ```json
    {
        "zone_name": null,
        "start_time": "2024-01-14T10:00:00Z",
        "end_time": "2024-01-15T10:00:00Z",
        "metric_type": "hourly",
        "data_points": 24,
        "metrics": [...],
        "summary": {
            "total_entries": 450,
            "total_exits": 420,
            "peak_occupancy": 85,
            "avg_occupancy": 52.3,
            "avg_dwell_time": 35.2
        }
    }
    ```
    """
    metric_service = MetricService(db)
    
    # Set default time range
    if not end_time:
        end_time = datetime.utcnow()
    if not start_time:
        start_time = end_time - timedelta(hours=hours)
    
    metrics, total, summary = metric_service.get_metric_history(
        zone_name=zone_name,
        metric_type=metric_type,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size
    )
    
    return MetricHistoryResponse(
        zone_name=zone_name,
        start_time=start_time,
        end_time=end_time,
        metric_type=metric_type,
        data_points=total,
        metrics=[
            MetricResponse(
                metric_id=m.metric_id,
                timestamp=m.timestamp,
                period_start=m.period_start,
                period_end=m.period_end,
                avg_dwell_time=m.avg_dwell_time,
                min_dwell_time=m.min_dwell_time,
                max_dwell_time=m.max_dwell_time,
                entry_rate=m.entry_rate,
                exit_rate=m.exit_rate,
                throughput=m.throughput,
                total_entries=m.total_entries,
                total_exits=m.total_exits,
                net_flow=m.net_flow,
                peak_occupancy=m.peak_occupancy,
                avg_occupancy=m.avg_occupancy,
                zone_name=m.zone_name,
                metric_type=m.metric_type,
                sample_count=m.sample_count
            )
            for m in metrics
        ],
        summary=summary
    )


@router.get(
    "/dashboard",
    summary="Get Dashboard Analytics",
    description="Get comprehensive analytics for dashboard."
)
async def get_dashboard_analytics(
    db: Session = Depends(get_db)
):
    """
    Get comprehensive analytics for dashboard display.
    
    Returns:
        Complete analytics package for dashboard
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_dashboard_analytics()


@router.get(
    "/flow",
    summary="Get Flow Analysis",
    description="Analyze patient flow patterns."
)
async def get_flow_analysis(
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get patient flow analysis.
    
    Returns:
        Hourly entry/exit breakdown
    """
    analytics_service = AnalyticsService(db)
    return analytics_service.get_flow_analysis(hours=hours)


@router.get(
    "/zone/{zone_name}",
    summary="Get Zone Analytics",
    description="Get detailed analytics for a specific zone."
)
async def get_zone_analytics(
    zone_name: str,
    hours: int = Query(24, ge=1, le=168, description="Hours to analyze"),
    db: Session = Depends(get_db)
):
    """
    Get detailed analytics for a zone.
    
    Returns:
        Zone-specific metrics and trends
    """
    analytics_service = AnalyticsService(db)
    data = analytics_service.get_zone_analytics(zone_name, hours)
    
    if "error" in data:
        raise HTTPException(status_code=404, detail=data["error"])
    
    return data


@router.get(
    "/peak-hours",
    summary="Get Peak Hours",
    description="Identify peak hours based on historical data."
)
async def get_peak_hours(
    days: int = Query(7, ge=1, le=30, description="Days to analyze"),
    db: Session = Depends(get_db)
):
    """
    Identify peak hours for the facility.
    
    Returns:
        Hourly occupancy averages
    """
    metric_service = MetricService(db)
    return {
        "days_analyzed": days,
        "peak_hours": metric_service.get_peak_hours(days=days)
    }


@router.post(
    "/calculate",
    summary="Calculate Metrics",
    description="Trigger hourly metric calculation."
)
async def calculate_metrics(
    zone_name: Optional[str] = Query(None, description="Zone (null for facility-wide)"),
    db: Session = Depends(get_db)
):
    """
    Manually trigger metric calculation.
    
    This is typically run by a background task,
    but can be triggered manually.
    """
    metric_service = MetricService(db)
    metric = metric_service.calculate_hourly_metrics(zone_name)
    
    return {
        "message": "Metrics calculated successfully",
        "metric_id": metric.metric_id,
        "zone": zone_name or "facility",
        "timestamp": metric.timestamp.isoformat()
    }
