"""
PatientPath AI - ID Generation Service
========================================
Generates unique IDs in XXXX-NNNN format (first 4 letters of username + 4-digit number).
"""

from sqlalchemy.orm import Session
from models.user import User


class IDGenerationService:

    @staticmethod
    def generate_id(username: str, db: Session) -> str:
        # Extract first 4 alphabetic characters, uppercase
        prefix = ''.join(c for c in username.upper() if c.isalpha())[:4]
        prefix = prefix.ljust(4, 'X')  # pad with X if fewer than 4 letters

        # Find max existing number for this prefix
        existing = db.query(User).filter(
            User.generated_id.like(f"{prefix}-%")
        ).all()

        if existing:
            max_num = max(int(u.generated_id.split('-')[1]) for u in existing)
            next_num = max_num + 1
        else:
            next_num = 1001  # start at 1001 to ensure 4 digits

        return f"{prefix}-{next_num}"
