from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

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


# -------------------- CHAT SCHEMAS (new) --------------------
class ChatRequest(BaseModel):
    patient_id: int
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str
