"""
PatientPath AI - Analytics Service
==================================
Service for computing analytics and metrics.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.patient import Patient, PatientStatus
from models.zone import Zone
from models.occupancy import OccupancyLog
from models.metric import Metric


class AnalyticsService:
    """Service for computing analytics and metrics."""
    
    @staticmethod
    def get_live_metrics(db: Session) -> Dict[str, Any]:
        """Get real-time metrics for all zones."""
        zones = db.query(Zone).filter(Zone.is_active == True).all()
        
        total_occupancy = sum(z.current_occupancy for z in zones)
        total_capacity = sum(z.capacity_limit for z in zones)
        
        active_patients = db.query(Patient).filter(
            Patient.status != PatientStatus.EXITED
        ).count()
        
        # Calculate avg dwell time
        avg_dwell = AnalyticsService._calculate_avg_dwell_time(db)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_occupancy": total_occupancy,
            "total_capacity": total_capacity,
            "occupancy_rate": round(total_occupancy / total_capacity, 3) if total_capacity > 0 else 0,
            "active_patients": active_patients,
            "zones": [z.to_dict() for z in zones],
            "avg_dwell_time_minutes": avg_dwell
        }
    
    @staticmethod
    def get_hourly_metrics(db: Session, hours: int = 24) -> List[Dict[str, Any]]:
        """Get hourly aggregated metrics."""
        since = datetime.now() - timedelta(hours=hours)
        
        metrics = db.query(Metric).filter(
            Metric.timestamp >= since,
            Metric.metric_type == "hourly"
        ).order_by(Metric.timestamp.desc()).all()
        
        return [m.to_dict() for m in metrics]
    
    @staticmethod
    def get_zone_analytics(db: Session, zone_name: str, hours: int = 24) -> Dict[str, Any]:
        """Get analytics for a specific zone."""
        since = datetime.now() - timedelta(hours=hours)
        
        logs = db.query(OccupancyLog).filter(
            OccupancyLog.zone_name == zone_name,
            OccupancyLog.timestamp >= since
        ).all()
        
        if not logs:
            return {
                "zone_name": zone_name,
                "period_hours": hours,
                "data_points": 0,
                "avg_occupancy": 0,
                "peak_occupancy": 0,
                "total_entries": 0,
                "total_exits": 0
            }
        
        counts = [log.people_count for log in logs]
        
        return {
            "zone_name": zone_name,
            "period_hours": hours,
            "data_points": len(logs),
            "avg_occupancy": round(sum(counts) / len(counts), 2),
            "peak_occupancy": max(counts),
            "min_occupancy": min(counts),
            "total_entries": sum(log.entry_count or 0 for log in logs),
            "total_exits": sum(log.exit_count or 0 for log in logs)
        }
    
    @staticmethod
    def _calculate_avg_dwell_time(db: Session) -> float:
        """Calculate average dwell time for exited patients."""
        exited = db.query(Patient).filter(
            Patient.status == PatientStatus.EXITED,
            Patient.exit_time.isnot(None)
        ).all()
        
        if not exited:
            return 0.0
        
        total_dwell = sum(
            (p.exit_time - p.entry_time).total_seconds() / 60
            for p in exited if p.exit_time and p.entry_time
        )
        
        return round(total_dwell / len(exited), 2)
    
    @staticmethod
    def get_dashboard_summary(db: Session) -> Dict[str, Any]:
        """Get summary data for dashboard display."""
        total_patients = db.query(Patient).count()
        active_patients = db.query(Patient).filter(
            Patient.status != PatientStatus.EXITED
        ).count()
        
        zones = db.query(Zone).filter(Zone.is_active == True).all()
        total_occupancy = sum(z.current_occupancy for z in zones)
        total_capacity = sum(z.capacity_limit for z in zones)
        
        avg_dwell = AnalyticsService._calculate_avg_dwell_time(db)
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_patients": total_patients,
            "active_patients": active_patients,
            "total_zones": len(zones),
            "total_occupancy": total_occupancy,
            "total_capacity": total_capacity,
            "occupancy_rate": round(total_occupancy / total_capacity, 3) if total_capacity > 0 else 0,
            "avg_dwell_time_minutes": avg_dwell,
            "zones": [z.to_dict() for z in zones]
        }
