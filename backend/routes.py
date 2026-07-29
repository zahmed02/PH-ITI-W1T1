from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, List
import os
import shutil
from datetime import datetime

from backend.database import get_db
from backend.models import Doctor, Patient, DoctorAvailability, Appointment, Review, User, Notification, DoctorTimeOff, AppointmentTransfer
from backend.availability import get_schedule_preview, parse_iso_date
from backend.booking import book_appointment_by_id, build_slip_pdf_for_appointment
from backend.appointment_actions import cancel_appointment, set_doctor_day_off, propose_transfer, confirm_transfer, decline_transfer
from backend.appointment_numbering import compute_display_appointment_id
from backend.schemas import (
    DoctorResponse, DoctorWithDetails,
    PatientResponse,
    AppointmentCreate, AppointmentResponse,
    ReviewCreate, ReviewResponse,
    BookAppointmentRequest, BookAppointmentResult,
    NotificationOut,
    CancelAppointmentRequest, CancelAppointmentResult,
    DayOffRequest, DayOffResult,
    ProposeTransferRequest, TransferActionResult, TransferOut,
    AppointmentSlipRow,
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
    # of any patient (e.g. entering a phone-in review) and is trusted to
    # skip the eligibility check below.
    if current_user.role == "patient":
        if current_user.patient_id != review.patient_id:
            raise HTTPException(status_code=403, detail="You can only submit reviews as yourself.")

        # A patient may only review a doctor AFTER an appointment time with
        # that doctor has actually passed - can't review a visit that
        # hasn't happened yet.
        has_past_appointment = db.query(Appointment).filter(
            Appointment.patient_id == review.patient_id,
            Appointment.doctor_id == review.doctor_id,
            Appointment.appointment_time < datetime.now(),
            Appointment.status != "cancelled",
        ).first()
        if not has_past_appointment:
            raise HTTPException(
                status_code=403,
                detail="You can only review a doctor after an appointment time with them has passed.",
            )
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


# -------------------- APPOINTMENT SLIP (PDF) --------------------

def _ensure_can_access_appointment(current_user: User, appointment: Appointment):
    """Admin, the owning doctor, or the owning patient may access a given appointment's details/PDF."""
    if current_user.role == "admin":
        return
    if current_user.role == "doctor" and current_user.doctor_id == appointment.doctor_id:
        return
    if current_user.role == "patient" and current_user.patient_id == appointment.patient_id:
        return
    raise HTTPException(status_code=403, detail="You do not have permission to view this appointment.")


@router.get("/appointments/{appointment_id}/slip.pdf")
def get_appointment_slip_pdf(
    appointment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Streams the same PDF slip that was emailed on booking. Available to
    the owning patient, the owning doctor (this is the doctor's "3rd menu
    option" view), or an admin.
    """
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    _ensure_can_access_appointment(current_user, appointment)

    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()
    if not doctor or not patient:
        raise HTTPException(status_code=404, detail="Related doctor/patient record not found")

    pdf_bytes = build_slip_pdf_for_appointment(db, appointment, doctor, patient)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="appointment_slip_{appointment_id}.pdf"'},
    )


@router.get("/doctors/{doctor_id}/slips", response_model=List[AppointmentSlipRow])
def list_doctor_slips(
    doctor_id: int,
    upcoming_only: bool = True,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists a doctor's own appointments for the 'Appointment Slips' menu page - the doctor themselves or an admin."""
    ensure_can_access_doctor_data(current_user, doctor_id)

    query = db.query(Appointment).filter(Appointment.doctor_id == doctor_id)
    if upcoming_only:
        query = query.filter(Appointment.appointment_time >= datetime.now())
    appointments = query.order_by(Appointment.appointment_time).limit(100).all()

    rows = []
    for appt in appointments:
        patient = db.query(Patient).filter(Patient.id == appt.patient_id).first()
        rows.append(AppointmentSlipRow(
            id=appt.id,
            display_appointment_id=compute_display_appointment_id(db, appt),
            patient_name=f"{patient.first_name} {patient.last_name}" if patient else "Unknown",
            appointment_time=appt.appointment_time,
            status=appt.status,
        ))
    return rows


# -------------------- CANCELLATION --------------------

@router.post("/appointments/{appointment_id}/cancel", response_model=CancelAppointmentResult)
def cancel_appointment_endpoint(
    appointment_id: int,
    payload: CancelAppointmentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # A doctor may only cancel their OWN appointments; admin may cancel any.
    ensure_can_access_doctor_data(current_user, appointment.doctor_id)

    result = cancel_appointment(db, appointment, reason=payload.reason or "")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


# -------------------- DAY OFF --------------------

@router.post("/doctors/{doctor_id}/time-off", response_model=DayOffResult)
def set_day_off_endpoint(
    doctor_id: int,
    payload: DayOffRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """
    Marks doctor_id unavailable for one date, cancelling (and emailing
    patients for) any existing bookings that day. The doctor themselves
    or an admin may call this.
    """
    ensure_can_access_doctor_data(current_user, doctor_id)

    off_date = parse_iso_date(payload.date)
    if not off_date:
        raise HTTPException(status_code=400, detail="date must be an ISO date (YYYY-MM-DD).")
    if off_date < datetime.now().date():
        raise HTTPException(status_code=400, detail="Cannot mark a day off in the past.")

    result = set_doctor_day_off(db, doctor_id, off_date, reason=payload.reason or "")
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/doctors/{doctor_id}/time-off")
def list_day_off(
    doctor_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Public (any logged-in role) - patients/admins benefit from seeing a doctor's upcoming days off too."""
    rows = db.query(DoctorTimeOff).filter(
        DoctorTimeOff.doctor_id == doctor_id,
        DoctorTimeOff.off_date >= datetime.now().date(),
    ).order_by(DoctorTimeOff.off_date).all()
    return [{"date": r.off_date.isoformat(), "reason": r.reason} for r in rows]


# -------------------- TRANSFERS --------------------

@router.post("/appointments/{appointment_id}/transfer", response_model=TransferActionResult)
def propose_transfer_endpoint(
    appointment_id: int,
    payload: ProposeTransferRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """The (from) doctor proposes transferring a cancelled appointment to a same-specialty colleague."""
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    ensure_can_access_doctor_data(current_user, appointment.doctor_id)

    from_doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    result = propose_transfer(db, appointment, from_doctor, payload.to_doctor_id)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.get("/appointment-transfers/incoming", response_model=List[TransferOut])
def list_incoming_transfers(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    """Pending transfer requests addressed TO the current doctor, for them to confirm/decline."""
    if current_user.role != "doctor" or not current_user.doctor_id:
        return []

    transfers = db.query(AppointmentTransfer).filter(
        AppointmentTransfer.to_doctor_id == current_user.doctor_id,
        AppointmentTransfer.status == "pending",
    ).order_by(AppointmentTransfer.created_at.desc()).all()

    rows = []
    for t in transfers:
        appt = db.query(Appointment).filter(Appointment.id == t.appointment_id).first()
        from_doc = db.query(Doctor).filter(Doctor.id == t.from_doctor_id).first()
        patient = db.query(Patient).filter(Patient.id == appt.patient_id).first() if appt else None
        if not appt or not from_doc or not patient:
            continue
        rows.append(TransferOut(
            id=t.id,
            appointment_id=t.appointment_id,
            from_doctor_id=t.from_doctor_id,
            from_doctor_name=f"Dr. {from_doc.first_name} {from_doc.last_name}",
            to_doctor_id=t.to_doctor_id,
            status=t.status,
            created_at=t.created_at,
            patient_name=f"{patient.first_name} {patient.last_name}",
            appointment_time=appt.appointment_time,
        ))
    return rows


@router.post("/appointment-transfers/{transfer_id}/confirm", response_model=TransferActionResult)
def confirm_transfer_endpoint(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    transfer = db.query(AppointmentTransfer).filter(AppointmentTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    # Only the RECEIVING doctor (or admin) may confirm it.
    ensure_can_access_doctor_data(current_user, transfer.to_doctor_id)

    result = confirm_transfer(db, transfer)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result


@router.post("/appointment-transfers/{transfer_id}/decline", response_model=TransferActionResult)
def decline_transfer_endpoint(
    transfer_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_doctor_or_admin),
):
    transfer = db.query(AppointmentTransfer).filter(AppointmentTransfer.id == transfer_id).first()
    if not transfer:
        raise HTTPException(status_code=404, detail="Transfer not found")

    ensure_can_access_doctor_data(current_user, transfer.to_doctor_id)

    result = decline_transfer(db, transfer)
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["message"])
    return result