"""
PatientPath AI - User Schemas
==============================
Pydantic schemas for user registration, login, and approval.
"""

from pydantic import BaseModel, field_validator
from typing import Optional


class UserRegister(BaseModel):
    username: str
    password: str
    confirm_password: str
    mobile: Optional[str] = None
    role: str  # patient, doctor, staff
    department: Optional[str] = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, v):
        if v not in ("patient", "doctor", "staff"):
            raise ValueError("Role must be patient, doctor, or staff. Admin cannot self-register.")
        return v

    @field_validator("confirm_password")
    @classmethod
    def passwords_match(cls, v, info):
        if "password" in info.data and v != info.data["password"]:
            raise ValueError("Passwords do not match")
        return v


class UserLogin(BaseModel):
    login_id: str  # mobile for patient, generated_id for others
    password: str
    role: str


class AdminLogin(BaseModel):
    admin_id: str  # generated_id like ADMI-0001
    password: str


class ApprovalAction(BaseModel):
    approver_id: int


class UserResponse(BaseModel):
    id: int
    username: str
    generated_id: str
    role: str
    department: Optional[str] = None
    status: str
    mobile: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True
