import re
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from backend.models import Doctor, Patient, Appointment, Notification
from backend.availability import get_doctor_working_hours, _compute_free_slots
from backend.email_service import send_appointment_confirmation
from backend.appointment_numbering import compute_display_appointment_id, compute_seniority_number, compute_mr_number
from backend.pdf_service import generate_appointment_slip_pdf
import logging

logger = logging.getLogger(__name__)


def build_slip_pdf_for_appointment(db: Session, appointment: Appointment, doctor: Doctor, patient: Patient) -> bytes:
    """
    Shared by both a fresh booking confirmation and a confirmed transfer's
    new-appointment confirmation - same slip format either way.
    """
    now = datetime.now()
    return generate_appointment_slip_pdf(
        doctor_name=f"Dr. {doctor.first_name} {doctor.last_name}",
        department=doctor.specialty,
        patient_name=f"{patient.first_name} {patient.last_name}",
        appointment_date_str=appointment.appointment_time.strftime("%d-%b-%y"),
        appointment_time_str=appointment.appointment_time.strftime("%I:%M %p"),
        day_name=appointment.appointment_time.strftime("%A"),
        seniority_no=compute_seniority_number(db, appointment),
        mr_no=compute_mr_number(patient),
        display_appointment_id=compute_display_appointment_id(db, appointment),
        booking_date_str=(appointment.created_at or now).strftime("%d-%b-%y"),
        printed_at_str=now.strftime("%d-%b-%y %H:%M"),
    )


def clean_doctor_name(raw: str) -> str:
    """
    Normalize a doctor name as it comes out of the LLM's tool-call
    arguments. The model copies the name straight from the user's
    sentence, so it can arrive as "Dr. Chen." (trailing period from the
    end of the sentence), "dr chen?", etc. Strip the "Dr."/"Doctor"
    prefix AND any leading/trailing punctuation, or ILIKE lookups miss
    real matches (e.g. searching for "Chen." never matches "Chen").
    """
    if not raw:
        return ""
    name = raw.strip()
    name = re.sub(r'^[^\w]+', '', name)   # strip leading punctuation/quotes first...
    name = re.sub(r'^(dr\.?|doctor)\s+', '', name, flags=re.IGNORECASE)  # ...so "Dr." prefix is recognized
    name = re.sub(r'[^\w]+$', '', name)   # strip trailing punctuation (. ? ! etc.)
    return name.strip()


def find_doctors_by_name(db: Session, doctor_name: str) -> list:
    """
    Returns ALL doctors matching the given name - callers must handle
    the 0 / 1 / many-results cases themselves rather than silently
    picking one. This matters because names like "Martinez" can match
    more than one doctor.
    """
    clean = clean_doctor_name(doctor_name)
    if not clean:
        return []

    full_matches = db.query(Doctor).filter(
        func.concat(Doctor.first_name, ' ', Doctor.last_name).ilike(f"%{clean}%")
    ).all()
    if full_matches:
        return full_matches

    return db.query(Doctor).filter(
        (Doctor.first_name.ilike(f"%{clean}%")) | (Doctor.last_name.ilike(f"%{clean}%"))
    ).all()


def find_doctor_by_name(db: Session, doctor_name: str):
    """
    Convenience wrapper for callers that just want a single doctor.
    Returns the doctor ONLY if the name is unambiguous; returns None for
    both "not found" and "multiple matches" - use find_doctors_by_name
    directly if you need to tell those two cases apart (as the chat
    tools do, so the assistant can ask the user to disambiguate instead
    of guessing).
    """
    matches = find_doctors_by_name(db, doctor_name)
    if len(matches) == 1:
        return matches[0]
    return None


def _book_appointment_core(db: Session, doctor: Doctor, patient_id: int, date_expr: str, time_expr: str) -> dict:
    """
    Shared validation + creation logic once a specific Doctor row is
    already resolved (by name for the AI assistant, or by id for the
    admin's direct booking form / a future patient self-booking button).
    Every booking path in the app funnels through here, which is what
    guarantees a doctor notification and a patient confirmation email are
    ALWAYS produced together with the appointment - no booking path can
    accidentally skip them.
    """
    try:
        date_obj = datetime.strptime(date_expr, "%Y-%m-%d").date()
        time_obj = datetime.strptime(time_expr, "%H:%M").time()
        appointment_datetime = datetime.combine(date_obj, time_obj)
    except (ValueError, TypeError) as e:
        logger.error(f"Date/time parsing failed: {e}")
        return {"success": False, "message": "Could not understand the date or time format. Please use YYYY-MM-DD for date and HH:MM (24-hour) for time."}

    if appointment_datetime < datetime.now():
        return {"success": False, "message": "That date and time is in the past. Please choose a future slot."}

    working = get_doctor_working_hours(doctor.id, date_obj, db)
    if not working:
        return {"success": False, "message": f"Dr. {doctor.first_name} {doctor.last_name} is not working on {date_obj.strftime('%A')}."}

    # Check the exact requested slot is free (datetime comparison, not string matching)
    free_slots = _compute_free_slots(doctor.id, date_obj, db, slot_duration=60)
    if appointment_datetime not in free_slots:
        available_str = ", ".join(s.strftime("%I:%M %p") for s in free_slots) or "no slots left that day"
        return {
            "success": False,
            "message": f"The requested time {appointment_datetime.strftime('%I:%M %p')} is not available. "
                       f"Available times on {date_obj.strftime('%Y-%m-%d')}: {available_str}."
        }

    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        return {"success": False, "message": f"No patient found with ID {patient_id}."}

    try:
        new_app = Appointment(
            doctor_id=doctor.id,
            patient_id=patient_id,
            appointment_time=appointment_datetime,
            status="scheduled"
        )
        db.add(new_app)
        db.flush()  # assigns new_app.id without committing yet

        # A doctor notification is created in the SAME transaction as the
        # appointment - if either fails, both roll back together, so a
        # doctor can never end up with a booking that has no notification.
        notification_message = (
            f"New appointment: {patient.first_name} {patient.last_name} booked with you on "
            f"{appointment_datetime.strftime('%A, %Y-%m-%d')} at {appointment_datetime.strftime('%I:%M %p')}."
        )
        db.add(Notification(
            doctor_id=doctor.id,
            appointment_id=new_app.id,
            message=notification_message,
        ))

        db.commit()
        db.refresh(new_app)
    except Exception as e:
        db.rollback()
        logger.error(f"Booking insertion failed: {e}")
        return {"success": False, "message": "An error occurred while booking. Please try again later."}

    # Email is sent AFTER the commit succeeds, and is best-effort - a slow
    # or unconfigured mail server must never undo an otherwise-successful
    # booking. send_appointment_confirmation() never raises; it returns
    # False on any failure, which we just note in the response.
    pdf_bytes = build_slip_pdf_for_appointment(db, new_app, doctor, patient)
    email_sent = send_appointment_confirmation(patient, doctor, pdf_bytes)

    return {
        "success": True,
        "message": f"Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name} on {appointment_datetime.strftime('%Y-%m-%d at %I:%M %p')}.",
        "appointment_id": new_app.id,
        "doctor_id": doctor.id,
        "doctor_name": f"{doctor.first_name} {doctor.last_name}",
        "patient_id": patient.id,
        "date": appointment_datetime.strftime("%Y-%m-%d"),
        "time": appointment_datetime.strftime("%I:%M %p"),
        "confirmation_email_sent": email_sent,
    }


def book_appointment(db: Session, doctor_name: str, patient_id: int, date_expr: str, time_expr: str) -> dict:
    """
    Name-based booking - used by the AI assistant, which only has a
    doctor's name from natural language, not their id.
    """
    matches = find_doctors_by_name(db, doctor_name)
    if len(matches) == 0:
        return {"success": False, "message": f"Could not find a doctor named '{doctor_name}'."}
    if len(matches) > 1:
        options = ", ".join(f"Dr. {d.first_name} {d.last_name} ({d.specialty})" for d in matches)
        return {
            "success": False,
            "ambiguous": True,
            "message": f"'{doctor_name}' matches more than one doctor: {options}. Please specify which one."
        }
    return _book_appointment_core(db, matches[0], patient_id, date_expr, time_expr)


def book_appointment_by_id(db: Session, doctor_id: int, patient_id: int, date_expr: str, time_expr: str) -> dict:
    """
    ID-based booking - used by the admin's direct booking form (and
    reusable later for a patient self-booking UI), where the doctor is
    already chosen from a dropdown rather than typed as free text.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return {"success": False, "message": f"No doctor found with ID {doctor_id}."}
    return _book_appointment_core(db, doctor, patient_id, date_expr, time_expr)