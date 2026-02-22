"""Zone Service"""
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Optional
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models.zone import Zone
from schemas.zone import ZoneCreate, ZoneUpdate


class ZoneService:
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, skip: int = 0, limit: int = 100) -> List[Zone]:
        return self.db.query(Zone).offset(skip).limit(limit).all()
    
    def get_active(self) -> List[Zone]:
        return self.db.query(Zone).filter(Zone.is_active == True).all()
    
    def get_by_id(self, zone_id: int) -> Optional[Zone]:
        return self.db.query(Zone).filter(Zone.id == zone_id).first()
    
    def get_by_name(self, zone_name: str) -> Optional[Zone]:
        return self.db.query(Zone).filter(Zone.zone_name == zone_name).first()

    # Alias for router compatibility
    def get_zone_by_name(self, zone_name: str) -> Optional[Zone]:
        return self.get_by_name(zone_name)
    
    def create(self, zone_data: ZoneCreate) -> Zone:
        zone = Zone(
            zone_name=zone_data.zone_name,
            display_name=zone_data.display_name,
            description=zone_data.description,
            capacity_limit=zone_data.capacity_limit,
            zone_type=zone_data.zone_type,
            floor_number=zone_data.floor_number,
            building=zone_data.building
        )
        self.db.add(zone)
        self.db.commit()
        self.db.refresh(zone)
        return zone
    
    def update(self, zone_id: int, zone_data: ZoneUpdate) -> Optional[Zone]:
        zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return None
        
        update_data = zone_data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(zone, key, value)
        
        zone.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(zone)
        return zone
    
    def update_occupancy(self, zone_name: str, new_count: int) -> Optional[Zone]:
        zone = self.db.query(Zone).filter(Zone.zone_name == zone_name).first()
        if not zone:
            return None
        zone.current_occupancy = new_count
        zone.updated_at = datetime.now()
        self.db.commit()
        self.db.refresh(zone)
        return zone
    
    def delete(self, zone_id: int) -> bool:
        zone = self.db.query(Zone).filter(Zone.id == zone_id).first()
        if not zone:
            return False
        self.db.delete(zone)
        self.db.commit()
        return True
    
    def count(self) -> int:
        return self.db.query(Zone).count()
