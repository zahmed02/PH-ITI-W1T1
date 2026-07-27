from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import os
import shutil
from datetime import datetime

from backend.database import get_db
from backend.models import Doctor, Patient, DoctorAvailability, Appointment, Review, User, Notification
from backend.availability import get_schedule_preview, parse_iso_date
from backend.booking import book_appointment_by_id
from backend.schemas import (
    DoctorResponse, DoctorWithDetails,
    PatientResponse,
    AppointmentCreate, AppointmentResponse,
    ReviewCreate, ReviewResponse,
    BookAppointmentRequest, BookAppointmentResult,
    NotificationOut,
)
from backend.auth import (
    get_current_user,
    require_admin,
    require_doctor_or_admin,
    ensure_can_access_doctor_data,
    ensure_can_access_patient_data,
)

router = APIRouter()

# -------------------- DOCTOR ENDPOINTS --------------------
# Public profile info (name, specialty, experience, rating, bio) is
# visible to any logged-in role - patients need this to browse/book,
# doctors need it to see colleagues for referrals, admins need it too.
# "Logged in" is the only bar here; no role restriction.

@router.get("/doctors/", response_model=List[DoctorResponse])
def get_all_doctors(
    skip: int = 0,
    limit: int = 100,
    specialty: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Doctor)
    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    return query.offset(skip).limit(limit).all()

@router.get("/doctors/{doctor_id}", response_model=DoctorWithDetails)
def get_doctor(doctor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doctor_id).scalar()
    review_count = db.query(func.count(Review.id)).filter(Review.doctor_id == doctor_id).scalar()
    
    result = DoctorWithDetails.model_validate(doctor)
    result.avg_rating = float(avg_rating) if avg_rating else 0.0
    result.review_count = review_count or 0
    result.reviews = doctor.reviews
    return result

@router.get("/doctors/search/", response_model=List[DoctorResponse])
def search_doctors(
    specialty: Optional[str] = Query(None),
    min_experience: Optional[int] = Query(None),
    min_rating: Optional[float] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Doctor)
    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    if min_experience:
        query = query.filter(Doctor.years_of_experience >= min_experience)
    
    doctors = query.all()
    if min_rating:
        result = []
        for doc in doctors:
            avg = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doc.id).scalar()
            if avg and float(avg) >= min_rating:
                result.append(doc)
            elif not avg and min_rating <= 0:
                result.append(doc)
        return result
    return doctors

@router.post("/doctors/{doctor_id}/image")
async def upload_doctor_image(
    doctor_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    # A doctor may only update their OWN photo; admin may update any.
    ensure_can_access_doctor_data(current_user, doctor_id)

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    
    # Validate file type
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image")
    
    # Create directory if not exists
    upload_dir = "static/images/doctors"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Generate unique filename
    ext = os.path.splitext(file.filename)[1]
    filename = f"doctor_{doctor_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}{ext}"
    file_path = os.path.join(upload_dir, filename)
    
    # Save file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Update database with relative path
    doctor.profile_image = f"/static/images/doctors/{filename}"
    db.commit()
    db.refresh(doctor)
    
    return {"message": "Image uploaded successfully", "profile_image": doctor.profile_image}

@router.get("/doctors/{doctor_id}/availability")
def get_doctor_availability(doctor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Public (any logged-in role) - patients need this to book, doctors/
    # admins need it too. This only returns working-hours slots, not
    # which specific patient holds a given slot.
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    availability = db.query(DoctorAvailability).filter(DoctorAvailability.doctor_id == doctor_id).all()
    return availability

@router.get("/doctors/{doctor_id}/schedule-preview")
def get_doctor_schedule_preview(
    doctor_id: int,
    week_start: str = Query(..., description="ISO date (YYYY-MM-DD) of the first day to show"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Privacy-safe booking view: returns which slots are available/booked
    per day, WITHOUT ever revealing which patient holds a booked slot.
    This is what the patient-facing booking calendar should call -
    GET /appointments/doctor/{id} (which does include real patient names)
    is restricted to the doctor themselves or an admin, on purpose.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")

    start_date = parse_iso_date(week_start)
    if not start_date:
        raise HTTPException(status_code=400, detail="week_start must be an ISO date (YYYY-MM-DD).")

    return get_schedule_preview(doctor_id, start_date, db)

# -------------------- PATIENT ENDPOINTS --------------------

@router.get("/patients/", response_model=List[PatientResponse])
def get_all_patients(
    skip: int = 0,
    limit: int = 200,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    # Unlike doctors, the patient list is NOT public - it's sensitive
    # personal data (names, emails, phone numbers). Admin-only, used for
    # the admin's "create patient" confirmation and the direct-booking
    # patient picker.
    return db.query(Patient).order_by(Patient.last_name, Patient.first_name).offset(skip).limit(limit).all()

# -------------------- APPOINTMENT ENDPOINTS --------------------

@router.get("/appointments/", response_model=List[AppointmentResponse])
def get_all_appointments(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(require_admin)):
    # Hospital-wide appointment list - admin only.
    return db.query(Appointment).offset(skip).limit(limit).all()

@router.get("/appointments/doctor/{doctor_id}", response_model=List[AppointmentResponse])
def get_appointments_by_doctor(doctor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # A doctor may only see their OWN appointments; admin may see any doctor's.
    ensure_can_access_doctor_data(current_user, doctor_id)

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db.query(Appointment).filter(Appointment.doctor_id == doctor_id).all()

@router.get("/appointments/patient/{patient_id}", response_model=List[AppointmentResponse])
def get_appointments_by_patient(patient_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # A patient may only see their OWN appointments; admin may see any patient's.
    ensure_can_access_patient_data(current_user, patient_id)

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    return db.query(Appointment).filter(Appointment.patient_id == patient_id).all()

@router.post("/appointments/", response_model=AppointmentResponse)
def create_appointment(appointment: AppointmentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """
    NOTE: this is a low-level raw insert - it does NOT check the doctor's
    working hours, does NOT check for double-booking, and does NOT create
    a doctor notification or send a patient confirmation email. Nothing
    in the frontend currently calls this. For any real booking, use
    POST /appointments/book instead, which runs the full validation +
    notification + email pipeline in backend/booking.py.
    """
    # A patient may only book for THEMSELVES; admin may book for anyone.
    if current_user.role == "patient":
        if current_user.patient_id != appointment.patient_id:
            raise HTTPException(status_code=403, detail="You can only book appointments for yourself.")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not have permission to book appointments.")

    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db_appointment = Appointment(**appointment.model_dump())
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)
    return db_appointment

@router.post("/appointments/book", response_model=BookAppointmentResult)
def book_appointment_endpoint(
    payload: BookAppointmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    The real, validated booking path - checks the doctor's working hours
    and for double-booking, then creates the appointment, a notification
    for the doctor, and (best-effort) a confirmation email to the
    patient, all through backend/booking.py::book_appointment_by_id.

    This is what the admin's direct "Book Appointment" form uses (no AI
    involved), and is reusable later for a patient self-booking button.
    """
    if current_user.role == "patient":
        if current_user.patient_id != payload.patient_id:
            raise HTTPException(status_code=403, detail="You can only book appointments for yourself.")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not have permission to book appointments directly. Contact an admin if you need an appointment booked.")

    result = book_appointment_by_id(db, payload.doctor_id, payload.patient_id, payload.date, payload.time)
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("message", "Could not book the appointment."))
    return result

# -------------------- REVIEW ENDPOINTS --------------------
# Reviews are public reading material (patients browsing doctors see
# them), so read access just requires being logged in, same as the
# doctor browse endpoints above.

@router.get("/reviews/", response_model=List[ReviewResponse])
def get_all_reviews(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(Review).offset(skip).limit(limit).all()

@router.get("/reviews/doctor/{doctor_id}", response_model=List[ReviewResponse])
def get_reviews_by_doctor(doctor_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return db.query(Review).filter(Review.doctor_id == doctor_id).all()

@router.post("/reviews/", response_model=ReviewResponse)
def create_review(review: ReviewCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # A patient may only leave a review AS THEMSELVES; admin may on behalf
    # of any patient (e.g. entering a phone-in review).
    # NOTE: "must have had a completed appointment with this doctor first"
    # is a deliberately deferred business rule - not enforced yet.
    if current_user.role == "patient":
        if current_user.patient_id != review.patient_id:
            raise HTTPException(status_code=403, detail="You can only submit reviews as yourself.")
    elif current_user.role != "admin":
        raise HTTPException(status_code=403, detail="You do not have permission to submit reviews.")

    doctor = db.query(Doctor).filter(Doctor.id == review.doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=404, detail="Doctor not found")
    patient = db.query(Patient).filter(Patient.id == review.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")
    
    db_review = Review(**review.model_dump())
    db.add(db_review)
    
    # Update doctor's average rating
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == review.doctor_id).scalar()
    doctor.rating = float(avg_rating) if avg_rating else 0.0
    db.commit()
    db.refresh(db_review)
    return db_review

# -------------------- NOTIFICATIONS --------------------
# Doctor-only: a doctor sees notifications about their OWN appointments.
# Created automatically by backend/booking.py on every successful
# booking, regardless of which path created it (AI chat, admin direct
# booking, or a future patient self-booking button).

@router.get("/notifications/me", response_model=List[NotificationOut])
def get_my_notifications(
    unread_only: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    if current_user.role == "doctor":
        if not current_user.doctor_id:
            raise HTTPException(status_code=400, detail="Your account isn't linked to a doctor record.")
        doctor_id = current_user.doctor_id
    else:
        # Admins don't have their own notification inbox (they aren't
        # tied to one doctor) - nothing to return.
        return []

    query = db.query(Notification).filter(Notification.doctor_id == doctor_id)
    if unread_only:
        query = query.filter(Notification.is_read.is_(False))
    return query.order_by(Notification.created_at.desc()).limit(50).all()

@router.post("/notifications/{notification_id}/read")
def mark_notification_read(
    notification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    notification = db.query(Notification).filter(Notification.id == notification_id).first()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    # A doctor may only mark their OWN notifications read; admin may mark any.
    ensure_can_access_doctor_data(current_user, notification.doctor_id)

    notification.is_read = True
    db.commit()
    return {"message": "Marked as read."}