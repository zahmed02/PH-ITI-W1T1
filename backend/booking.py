import re
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from backend.models import Doctor, Appointment
from backend.availability import get_doctor_working_hours, _compute_free_slots
import logging

logger = logging.getLogger(__name__)


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


def book_appointment(db: Session, doctor_name: str, patient_id: int, date_expr: str, time_expr: str) -> dict:
    """
    date_expr: ISO date string (YYYY-MM-DD)
    time_expr: time string in HH:MM (24-hour)
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
    doctor = matches[0]

    try:
        date_obj = datetime.strptime(date_expr, "%Y-%m-%d").date()
        time_obj = datetime.strptime(time_expr, "%H:%M").time()
        appointment_datetime = datetime.combine(date_obj, time_obj)
    except (ValueError, TypeError) as e:
        logger.error(f"Date/time parsing failed: {e}")
        return {"success": False, "message": "Could not understand the date or time format. Please use YYYY-MM-DD for date and HH:MM (24-hour) for time."}

    if appointment_datetime < datetime.now():
        return {"success": False, "message": "That date and time is in the past. Please choose a future slot."}

    day_of_week = date_obj.weekday()
    working = get_doctor_working_hours(doctor.id, day_of_week, db)
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

    try:
        new_app = Appointment(
            doctor_id=doctor.id,
            patient_id=patient_id,
            appointment_time=appointment_datetime,
            status="scheduled"
        )
        db.add(new_app)
        db.commit()
        db.refresh(new_app)
        return {
            "success": True,
            "message": f"Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name} on {appointment_datetime.strftime('%Y-%m-%d at %I:%M %p')}.",
            "appointment_id": new_app.id,
            "doctor_name": f"{doctor.first_name} {doctor.last_name}",
            "date": appointment_datetime.strftime("%Y-%m-%d"),
            "time": appointment_datetime.strftime("%I:%M %p")
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Booking insertion failed: {e}")
        return {"success": False, "message": "An error occurred while booking. Please try again later."}
