from pydantic import BaseModel, field_validator, EmailStr
from datetime import datetime
from typing import Optional, List, Literal

Role = Literal["admin", "doctor", "patient"]

# Doctor schemas
class DoctorBase(BaseModel):
    first_name: str
    last_name: str
    specialty: str
    years_of_experience: int
    bio: Optional[str] = None

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: int
    rating: float
    created_at: datetime
    profile_image: Optional[str] = None

    class Config:
        from_attributes = True

class DoctorWithDetails(DoctorResponse):
    avg_rating: Optional[float] = None
    review_count: int = 0
    reviews: List["ReviewResponse"] = []

# Patient schemas
class PatientBase(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: Optional[str] = None

class PatientCreate(PatientBase):
    pass

class PatientResponse(PatientBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# Appointment schemas
class AppointmentBase(BaseModel):
    doctor_id: int
    patient_id: int
    appointment_time: datetime
    status: str = "scheduled"
    notes: Optional[str] = None

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentResponse(AppointmentBase):
    id: int
    created_at: datetime
    doctor: Optional[DoctorResponse] = None
    patient: Optional[PatientResponse] = None

    class Config:
        from_attributes = True

# Review schemas
class ReviewBase(BaseModel):
    doctor_id: int
    patient_id: int
    rating: int
    comment: Optional[str] = None

class ReviewCreate(ReviewBase):
    pass

class ReviewResponse(ReviewBase):
    id: int
    created_at: datetime
    doctor: Optional[DoctorResponse] = None
    patient: Optional[PatientResponse] = None

    class Config:
        from_attributes = True

# Forward references
DoctorWithDetails.model_rebuild()


# -------------------- CHAT SCHEMAS --------------------
class ChatRequest(BaseModel):
    # patient_id is now OPTIONAL and, for role="patient" callers, is IGNORED
    # in favor of the patient linked to their login token - see
    # backend/chat_router.py. It's only actually used when an admin is
    # chatting on a patient's behalf.
    patient_id: Optional[int] = None
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str


# -------------------- AUTH SCHEMAS --------------------

def _validate_username(v: str) -> str:
    v = v.strip()
    if len(v) < 3:
        raise ValueError("Username must be at least 3 characters.")
    return v


def _validate_password(v: str) -> str:
    if len(v) < 8:
        raise ValueError("Password must be at least 8 characters.")
    return v


class PatientRegister(BaseModel):
    """
    Public self-registration - always creates a role="patient" account,
    plus the linked Patient record it needs (name/email/phone), atomically.
    There is deliberately no public way to register as "doctor" or "admin" -
    those accounts are created by an existing admin only (see
    AdminCreateDoctorRequest / AdminCreateAdminRequest below), otherwise
    anyone could sign up claiming to be a doctor or admin.
    """
    username: str
    password: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None

    _username_check = field_validator("username")(classmethod(lambda cls, v: _validate_username(v)))
    _password_check = field_validator("password")(classmethod(lambda cls, v: _validate_password(v)))


class UserLogin(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    role: Role
    doctor_id: Optional[int] = None
    patient_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: Role
    doctor_id: Optional[int] = None
    patient_id: Optional[int] = None


class DoctorAvailabilityBlock(BaseModel):
    """
    One weekly recurring working-hours block, used when an admin sets a
    new doctor's schedule at account-creation time.
    day_of_week: 0=Sunday ... 6=Saturday (matches the DB convention - see
    backend/availability.py::python_weekday_to_db_day for why).
    start_time / end_time: "HH:MM" 24-hour strings.
    """
    day_of_week: int
    start_time: str
    end_time: str

    @field_validator("day_of_week")
    @classmethod
    def _check_day(cls, v: int) -> int:
        if not (0 <= v <= 6):
            raise ValueError("day_of_week must be between 0 (Sunday) and 6 (Saturday).")
        return v


class AdminCreateDoctorRequest(BaseModel):
    """Admin-only: creates a Doctor record and its login account together, optionally with an initial weekly schedule."""
    username: str
    password: str
    first_name: str
    last_name: str
    specialty: str
    years_of_experience: int
    bio: Optional[str] = None
    availability: Optional[List[DoctorAvailabilityBlock]] = None

    _username_check = field_validator("username")(classmethod(lambda cls, v: _validate_username(v)))
    _password_check = field_validator("password")(classmethod(lambda cls, v: _validate_password(v)))


class AdminCreateAdminRequest(BaseModel):
    """Admin-only: creates another plain admin login (no doctor/patient link)."""
    username: str
    password: str

    _username_check = field_validator("username")(classmethod(lambda cls, v: _validate_username(v)))
    _password_check = field_validator("password")(classmethod(lambda cls, v: _validate_password(v)))


class AdminCreatePatientRequest(BaseModel):
    """
    Admin-only: creates a Patient record and its login account together,
    directly - no AI assistant involved. Mirrors AdminCreateDoctorRequest.
    """
    username: str
    password: str
    first_name: str
    last_name: str
    email: EmailStr
    phone: Optional[str] = None

    _username_check = field_validator("username")(classmethod(lambda cls, v: _validate_username(v)))
    _password_check = field_validator("password")(classmethod(lambda cls, v: _validate_password(v)))


# -------------------- DIRECT BOOKING (no AI) --------------------

class BookAppointmentRequest(BaseModel):
    """
    Used by POST /appointments/book - the direct, non-AI booking path.
    An admin may specify any doctor_id/patient_id; a patient calling this
    themselves may only specify their own patient_id (enforced in
    routes.py, same pattern as POST /appointments/).
    """
    doctor_id: int
    patient_id: int
    date: str   # ISO date, YYYY-MM-DD
    time: str   # 24-hour, HH:MM


class BookAppointmentResult(BaseModel):
    success: bool
    message: str
    ambiguous: Optional[bool] = None
    appointment_id: Optional[int] = None
    doctor_id: Optional[int] = None
    doctor_name: Optional[str] = None
    patient_id: Optional[int] = None
    date: Optional[str] = None
    time: Optional[str] = None
    confirmation_email_sent: Optional[bool] = None


# -------------------- NOTIFICATIONS --------------------

class NotificationOut(BaseModel):
    id: int
    appointment_id: Optional[int] = None
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True


# -------------------- CANCELLATION / DAY OFF / TRANSFERS --------------------

class CancelAppointmentRequest(BaseModel):
    reason: Optional[str] = None


class CancelAppointmentResult(BaseModel):
    success: bool
    message: str
    appointment_id: Optional[int] = None
    cancellation_email_sent: Optional[bool] = None


class DayOffRequest(BaseModel):
    date: str  # ISO date, YYYY-MM-DD
    reason: Optional[str] = None


class DayOffResult(BaseModel):
    success: bool
    message: str
    cancelled_appointment_ids: Optional[List[int]] = None


class ProposeTransferRequest(BaseModel):
    to_doctor_id: int


class TransferActionResult(BaseModel):
    success: bool
    message: str
    transfer_id: Optional[int] = None
    new_appointment_id: Optional[int] = None
    confirmation_email_sent: Optional[bool] = None


class TransferOut(BaseModel):
    id: int
    appointment_id: int
    from_doctor_id: int
    from_doctor_name: str
    to_doctor_id: int
    status: str
    created_at: datetime
    # Details about the appointment being transferred, so the receiving
    # doctor can decide without an extra lookup.
    patient_name: str
    appointment_time: datetime


class AppointmentSlipRow(BaseModel):
    """One row in a doctor's 'Appointment Slips' list view."""
    id: int
    display_appointment_id: str
    patient_name: str
    appointment_time: datetime
    status: str