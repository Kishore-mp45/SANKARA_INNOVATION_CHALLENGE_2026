"""Metric Service"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.metric import Metric
from models.patient import Patient, PatientStatus
from models.zone import Zone
from models.occupancy import OccupancyLog


class MetricService:
    @staticmethod
    def get_all(db: Session, skip: int = 0, limit: int = 100) -> List[Metric]:
        return db.query(Metric).order_by(desc(Metric.timestamp)).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_by_type(db: Session, metric_type: str, limit: int = 24) -> List[Metric]:
        return db.query(Metric).filter(
            Metric.metric_type == metric_type
        ).order_by(desc(Metric.timestamp)).limit(limit).all()
    
    @staticmethod
    def get_latest(db: Session) -> Optional[Metric]:
        return db.query(Metric).order_by(desc(Metric.timestamp)).first()
    
    @staticmethod
    def get_dashboard_summary(db: Session) -> Dict[str, Any]:
        """Get summary data for dashboard display."""
        total_patients = db.query(Patient).count()
        active_patients = db.query(Patient).filter(Patient.status != PatientStatus.EXITED).count()
        
        zones = db.query(Zone).filter(Zone.is_active == True).all()
        total_occupancy = sum(z.current_occupancy for z in zones)
        total_capacity = sum(z.capacity_limit for z in zones)
        
        # Calculate average dwell time for patients who have exited
        exited = db.query(Patient).filter(
            Patient.status == PatientStatus.EXITED,
            Patient.exit_time.isnot(None)
        ).all()
        
        if exited:
            total_dwell = sum(
                (p.exit_time - p.entry_time).total_seconds() / 60
                for p in exited if p.exit_time and p.entry_time
            )
            avg_dwell = total_dwell / len(exited)
        else:
            avg_dwell = 0
        
        return {
            "timestamp": datetime.now().isoformat(),
            "total_patients": total_patients,
            "active_patients": active_patients,
            "total_zones": len(zones),
            "total_occupancy": total_occupancy,
            "total_capacity": total_capacity,
            "occupancy_rate": round(total_occupancy / total_capacity, 3) if total_capacity > 0 else 0,
            "avg_dwell_time_minutes": round(avg_dwell, 2),
            "zones": [z.to_dict() for z in zones]
        }
    
    @staticmethod
    def create_snapshot(db: Session) -> Metric:
        """Create a metric snapshot of current state."""
        summary = MetricService.get_dashboard_summary(db)
        
        metric = Metric(
            timestamp=datetime.now(),
            metric_type="realtime",
            avg_occupancy=summary["occupancy_rate"] * 100,
            peak_occupancy=summary["total_occupancy"],
            avg_dwell_time=summary["avg_dwell_time_minutes"]
        )
        db.add(metric)
        db.commit()
        db.refresh(metric)
        return metric
