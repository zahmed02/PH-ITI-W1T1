"""
Authentication and role-based authorization for the patient portal.

Three roles, enforced end-to-end (not just hidden in the UI):
- "admin"   - full access to everything.
- "doctor"  - linked to exactly one Doctor row via User.doctor_id. Can only
              see/manage their own patients, appointments, and schedule.
- "patient" - linked to exactly one Patient row via User.patient_id. Can
              only see/manage their own appointments and profile.

Design notes:
- Passwords are hashed with bcrypt directly (not passlib, to avoid the
  passlib/bcrypt version-compatibility issues that trip up a lot of
  setups).
- Tokens are JWTs (PyJWT) carrying the user id, role, and a "tv"
  (token_version) claim. Logout increments the user's token_version in
  the DB, which immediately invalidates every token issued before that
  point - so logout is a real server-side revocation, not just "the
  client deletes its copy and hopes for the best."
- There is NO public endpoint to register as "doctor" or "admin" - only
  an existing admin can create those accounts (see admin_create_doctor /
  admin_create_admin below). The very first admin account is created by
  a one-time CLI script (backend/scripts/create_admin.py), not the API,
  since nothing exists yet to authorize creating it through the API.
"""
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt
from dotenv import load_dotenv
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Doctor, Patient, User
from backend.schemas import (
    AdminCreateAdminRequest,
    AdminCreateDoctorRequest,
    PatientRegister,
    TokenResponse,
    UserLogin,
    UserOut,
)

load_dotenv()
logger = logging.getLogger(__name__)

JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY")
if not JWT_SECRET_KEY:
    # Fine for local dev so the app doesn't just crash, but every restart
    # invalidates all existing tokens and it's not safe for production.
    JWT_SECRET_KEY = "insecure-dev-secret-change-me"
    logger.warning(
        "JWT_SECRET_KEY is not set in the environment - using an insecure "
        "default. Add JWT_SECRET_KEY=<a long random string> to your .env "
        "file before deploying this anywhere real."
    )

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 12  # 12 hours

router = APIRouter(prefix="/auth", tags=["Auth"])
bearer_scheme = HTTPBearer(auto_error=False)


# -------------------- password hashing --------------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        # Malformed hash in the DB - treat as a failed login, not a 500.
        return False


# -------------------- JWT --------------------

def create_access_token(user: User) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "username": user.username,
        "role": user.role,
        "tv": user.token_version,
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Not authenticated.")

    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Session expired. Please log in again.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid authentication token.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User no longer exists.")

    if payload.get("tv") != user.token_version:
        # The user (or another tab/device) logged out since this token was
        # issued - reject it even though it hasn't expired yet.
        raise HTTPException(status_code=401, detail="Session has been logged out. Please log in again.")

    return user


# -------------------- role-based authorization --------------------

def require_roles(*allowed_roles: str):
    """
    Dependency factory: raises 403 unless the logged-in user's role is one
    of allowed_roles. Use like: Depends(require_roles("admin", "doctor")).
    """
    def dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(status_code=403, detail="You do not have permission to do that.")
        return current_user
    return dependency


require_admin = require_roles("admin")
require_doctor = require_roles("doctor")
require_patient = require_roles("patient")
require_doctor_or_admin = require_roles("doctor", "admin")
require_patient_or_admin = require_roles("patient", "admin")


def ensure_can_access_doctor_data(current_user: User, doctor_id: int) -> None:
    """
    Raises 403 unless current_user is an admin, or is the doctor account
    linked to doctor_id. Use this to guard any endpoint that returns one
    specific doctor's private data (their patient list, appointment
    details, etc - NOT their public profile, which everyone can see).
    """
    if current_user.role == "admin":
        return
    if current_user.role == "doctor" and current_user.doctor_id == doctor_id:
        return
    raise HTTPException(status_code=403, detail="You do not have permission to view this doctor's data.")


def ensure_can_access_patient_data(current_user: User, patient_id: int) -> None:
    """
    Raises 403 unless current_user is an admin, or is the patient account
    linked to patient_id. Use this to guard any endpoint that returns one
    specific patient's private data (their appointments, profile, etc).
    """
    if current_user.role == "admin":
        return
    if current_user.role == "patient" and current_user.patient_id == patient_id:
        return
    raise HTTPException(status_code=403, detail="You do not have permission to view this patient's data.")


# -------------------- routes --------------------

@router.post("/register", response_model=TokenResponse)
def register(payload: PatientRegister, db: Session = Depends(get_db)):
    """
    Public self-registration. Always creates role="patient" - there is no
    public way to register as "doctor" or "admin" (see the /admin/* routes
    below for how those get created).
    """
    existing_user = db.query(User).filter(func.lower(User.username) == payload.username.lower()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="That username is already taken.")

    existing_patient = db.query(Patient).filter(func.lower(Patient.email) == payload.email.lower()).first()
    if existing_patient:
        raise HTTPException(status_code=400, detail="An account with that email already exists.")

    # Create the Patient record and its login account together, so a
    # logged-in patient always resolves to real patient data - no more
    # manually typing a "Patient ID" into the app.
    patient = Patient(
        first_name=payload.first_name,
        last_name=payload.last_name,
        email=payload.email,
        phone=payload.phone,
    )
    db.add(patient)
    db.flush()  # assigns patient.id without committing yet

    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role="patient",
        patient_id=patient.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user)
    return TokenResponse(
        access_token=token, user_id=user.id, username=user.username,
        role=user.role, doctor_id=user.doctor_id, patient_id=user.patient_id,
    )


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.username) == payload.username.strip().lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        # Deliberately identical message for "no such user" and "wrong
        # password" so login can't be used to enumerate valid usernames.
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    token = create_access_token(user)
    return TokenResponse(
        access_token=token, user_id=user.id, username=user.username,
        role=user.role, doctor_id=user.doctor_id, patient_id=user.patient_id,
    )


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    current_user.token_version += 1
    db.commit()
    return {"message": "Logged out successfully."}


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


# -------------------- admin-only account management --------------------

@router.post("/admin/doctors", response_model=UserOut)
def admin_create_doctor(
    payload: AdminCreateDoctorRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Admin-only. Creates a new Doctor record and its login account together.
    Returns the new account's info - NOT a token; the admin stays logged in
    as themselves, they are not logged in as the new doctor.
    """
    existing_user = db.query(User).filter(func.lower(User.username) == payload.username.lower()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="That username is already taken.")

    doctor = Doctor(
        first_name=payload.first_name,
        last_name=payload.last_name,
        specialty=payload.specialty,
        years_of_experience=payload.years_of_experience,
        bio=payload.bio,
    )
    db.add(doctor)
    db.flush()

    user = User(
        username=payload.username,
        hashed_password=hash_password(payload.password),
        role="doctor",
        doctor_id=doctor.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/admin/admins", response_model=UserOut)
def admin_create_admin(
    payload: AdminCreateAdminRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Admin-only. Creates another plain admin account (no doctor/patient link)."""
    existing_user = db.query(User).filter(func.lower(User.username) == payload.username.lower()).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="That username is already taken.")

    user = User(username=payload.username, hashed_password=hash_password(payload.password), role="admin")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/admin/users", response_model=list[UserOut])
def admin_list_users(current_user: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Admin-only. Lists every login account in the system, for the admin user-management view."""
    return db.query(User).order_by(User.role, User.username).all()