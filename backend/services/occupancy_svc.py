"""Occupancy Service"""
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
import json
import logging

from models.occupancy import OccupancyLog
from models.zone import Zone
from schemas.occupancy import OccupancyUpdate, OccupancyCreate

logger = logging.getLogger(__name__)

class OccupancyService:
    def __init__(self, db: Session):
        self.db = db

    def log_occupancy(self, data: OccupancyUpdate) -> OccupancyLog:
        """
        Log occupancy update from CV module.
        """
        try:
            # Get previous count for the zone
            zone = self.db.query(Zone).filter(Zone.zone_name == data.zone_name).first()
            previous_count = zone.current_occupancy if zone else 0
            
            # Calculate derived metrics if not provided
            entry_cnt = data.entry_count
            exit_cnt = data.exit_count
            
            # Create log entry
            log = OccupancyLog(
                zone_name=data.zone_name,
                people_count=data.people_count,
                previous_count=previous_count,
                entry_count=entry_cnt,
                exit_count=exit_cnt,
                confidence_score=data.confidence_score,
                source=data.source,
                unique_ids=json.dumps(data.unique_ids) if data.unique_ids else None,
                timestamp=datetime.utcnow()
            )
            self.db.add(log)
            
            # Update zone occupancy
            if zone:
                zone.current_occupancy = data.people_count
                zone.updated_at = datetime.utcnow()
            
            self.db.commit()
            self.db.refresh(log)
            return log
        except Exception as e:
            import traceback
            with open("c:/PATIENTPATH-AI/backend_error.txt", "w") as f:
                f.write(str(e) + "\n")
                traceback.print_exc(file=f)
            raise e

    def get_latest_log(self, zone_name: str) -> Optional[OccupancyLog]:
        return self.db.query(OccupancyLog).filter(
            OccupancyLog.zone_name == zone_name
        ).order_by(desc(OccupancyLog.timestamp)).first()
    
    # Placeholder/Stub methods for other router calls to avoid crashes if they are used
    
    def get_occupancy_history(self, zone_name=None, start_time=None, end_time=None, page=1, page_size=100) -> Tuple[List[OccupancyLog], int, Dict]:
        query = self.db.query(OccupancyLog)
        if zone_name:
            query = query.filter(OccupancyLog.zone_name == zone_name)
        if start_time:
            query = query.filter(OccupancyLog.timestamp >= start_time)
        if end_time:
            query = query.filter(OccupancyLog.timestamp <= end_time)
            
        total = query.count()
        logs = query.order_by(desc(OccupancyLog.timestamp)).offset((page-1)*page_size).limit(page_size).all()
        
        return logs, total, {}

    def get_current_occupancy(self) -> Dict:
        # Simplistic implementation
        total_occupancy = 0
        total_capacity = 0
        zones_data = []
        zones = self.db.query(Zone).filter(Zone.is_active == True).all()
        
        for zone in zones:
            total_occupancy += zone.current_occupancy
            total_capacity += zone.capacity_limit
            zones_data.append({
                "zone_name": zone.zone_name,
                "current_occupancy": zone.current_occupancy,
                "capacity_limit": zone.capacity_limit,
                "percentage": (zone.current_occupancy / zone.capacity_limit * 100) if zone.capacity_limit else 0,
                "status": "normal"
            })
            
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "total_occupancy": total_occupancy,
            "total_capacity": total_capacity,
            "overall_percentage": (total_occupancy / total_capacity * 100) if total_capacity else 0,
            "zones": zones_data
        }

    def get_hourly_aggregates(self, zone_name: str, hours: int) -> List[Dict]:
        return []

    def get_zone_trend(self, zone_name: str, minutes: int) -> Dict:
        return {"direction": "stable", "rate": 0}

    def log_batch_occupancy(self, data) -> List[OccupancyLog]:
        logs = []
        for update in data.updates:
            logs.append(self.log_occupancy(update))
        return logs
