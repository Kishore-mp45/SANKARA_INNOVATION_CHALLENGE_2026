"""
PatientPath AI - Auth Router
==============================
Handles registration, login, approval hierarchy, and user profiles.

Approval Hierarchy:
  - Admin approves/rejects Staff and Doctor only
  - Staff approves/rejects Patient only
"""

from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional
from werkzeug.security import generate_password_hash, check_password_hash

from database.database import get_db
from models.user import User
from schemas.user import UserRegister, UserLogin, AdminLogin, ApprovalAction
from services.id_generation_service import IDGenerationService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register")
async def register(data: UserRegister, db: Session = Depends(get_db)):
    """Register a new user. Account remains pending until approved."""

    # Validate mobile is provided for all roles
    if not data.mobile:
        raise HTTPException(status_code=400, detail="Mobile number is required")

    # Validate department for staff
    if data.role == "staff" and not data.department:
        raise HTTPException(status_code=400, detail="Department is required for staff")

    # Check if mobile already registered (for patients)
    if data.mobile:
        existing_mobile = db.query(User).filter(
            User.mobile == data.mobile, User.role == data.role
        ).first()
        if existing_mobile:
            raise HTTPException(status_code=400, detail="This mobile number is already registered")

    # Generate unique ID
    generated_id = IDGenerationService.generate_id(data.username, db)

    # Create user
    user = User(
        username=data.username,
        mobile=data.mobile,
        password_hash=generate_password_hash(data.password),
        role=data.role,
        department=data.department if data.role == "staff" else None,
        generated_id=generated_id,
        status="pending",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return {
        "message": "Registration submitted successfully. Your account is pending approval.",
        "user_id": user.id,
        "generated_id": user.generated_id,
        "status": "pending",
    }


@router.post("/login")
async def login(data: UserLogin, db: Session = Depends(get_db)):
    """Authenticate a user. Only approved accounts can login."""

    # Patient, Staff, Doctor login with mobile number
    user = db.query(User).filter(
        User.mobile == data.login_id, User.role == data.role
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Account not found. Please register first.")

    if user.role == "admin":
        raise HTTPException(status_code=403, detail="Admin must login via the admin portal (port 5000).")

    if not check_password_hash(user.password_hash, data.password):
        raise HTTPException(status_code=401, detail="Invalid password")

    if user.status == "pending":
        raise HTTPException(status_code=403, detail="Your account is pending approval. Please wait for approval.")

    if user.status == "rejected":
        raise HTTPException(status_code=403, detail="Your registration was rejected. Please contact administration.")

    return {
        "message": "Login successful",
        "user_id": user.id,
        "generated_id": user.generated_id,
        "username": user.username,
        "role": user.role,
        "department": user.department,
        "mobile": user.mobile,
        "status": user.status,
    }


@router.post("/admin-login")
async def admin_login(data: AdminLogin, db: Session = Depends(get_db)):
    """Dedicated admin login endpoint. Only accessible via admin portal (port 5000)."""

    user = db.query(User).filter(
        User.generated_id == data.admin_id, User.role == "admin"
    ).first()

    if not user:
        raise HTTPException(status_code=401, detail="Invalid Admin ID.")

    if not check_password_hash(user.password_hash, data.password):
        raise HTTPException(status_code=401, detail="Invalid password.")

    return {
        "message": "Admin login successful",
        "user_id": user.id,
        "generated_id": user.generated_id,
        "username": user.username,
        "role": "admin",
        "department": None,
        "mobile": user.mobile,
        "status": user.status,
    }


@router.get("/pending-approvals")
async def get_pending_approvals(
    role: Optional[str] = Query(None, description="Filter by role: patient, doctor, staff"),
    db: Session = Depends(get_db),
):
    """Get pending registrations. Admin sees doctors/staff, Registration staff sees patients."""
    query = db.query(User).filter(User.status == "pending")

    if role:
        query = query.filter(User.role == role)

    pending = query.order_by(User.created_at.desc()).all()
    return {"pending": [u.to_dict() for u in pending], "count": len(pending)}


@router.post("/approve/{user_id}")
async def approve_user(user_id: int, data: ApprovalAction, db: Session = Depends(get_db)):
    """Approve a pending registration."""

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != "pending":
        raise HTTPException(status_code=400, detail=f"User is already {user.status}")

    # Validate approver
    approver = db.query(User).filter(User.id == data.approver_id).first()
    if not approver:
        raise HTTPException(status_code=404, detail="Approver not found")

    # Enforce approval hierarchy
    if user.role in ("doctor", "staff"):
        if approver.role != "admin":
            raise HTTPException(status_code=403, detail="Only admin can approve doctor/staff registrations")
    elif user.role == "patient":
        if approver.role != "staff":
            raise HTTPException(status_code=403, detail="Only staff can approve patient registrations")

    user.status = "approved"
    user.approved_by = data.approver_id
    user.approved_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return {"message": f"{user.role.capitalize()} '{user.username}' has been approved.", "user": user.to_dict()}


@router.post("/reject/{user_id}")
async def reject_user(user_id: int, data: ApprovalAction, db: Session = Depends(get_db)):
    """Reject a pending registration."""

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.status != "pending":
        raise HTTPException(status_code=400, detail=f"User is already {user.status}")

    # Validate approver
    approver = db.query(User).filter(User.id == data.approver_id).first()
    if not approver:
        raise HTTPException(status_code=404, detail="Approver not found")

    # Enforce rejection hierarchy (same as approval)
    if user.role in ("doctor", "staff"):
        if approver.role != "admin":
            raise HTTPException(status_code=403, detail="Only admin can reject doctor/staff registrations")
    elif user.role == "patient":
        if approver.role != "staff":
            raise HTTPException(status_code=403, detail="Only staff can reject patient registrations")

    user.status = "rejected"
    user.approved_by = data.approver_id
    user.approved_at = datetime.utcnow()
    db.commit()

    return {"message": f"{user.role.capitalize()} '{user.username}' has been rejected."}


@router.get("/profile/{user_id}")
async def get_profile(user_id: int, db: Session = Depends(get_db)):
    """Get user profile details."""

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user.to_dict()


@router.get("/pending-count")
async def get_pending_count(
    role: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Get count of pending approvals (for badge display)."""
    query = db.query(User).filter(User.status == "pending")
    if role:
        query = query.filter(User.role == role)
    count = query.count()
    return {"count": count}
