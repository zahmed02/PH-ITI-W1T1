from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import re
import logging

from backend.models import Doctor, Appointment
from backend.availability import get_available_slots, get_doctor_working_hours
from backend.date_parser import parse_date_expression, parse_time_expression

logger = logging.getLogger(__name__)

def clean_doctor_name(name: str) -> str:
    """Remove titles like 'Dr.', 'Dr', 'Doctor' and extra spaces."""
    # Remove common titles
    cleaned = re.sub(r'\b(Dr\.?|Doctor|Prof\.?|Professor)\s+', '', name, flags=re.IGNORECASE)
    # Remove extra spaces
    cleaned = ' '.join(cleaned.split())
    return cleaned.strip()

def find_doctor_by_name(db: Session, name: str):
    """
    Find a doctor by partial name match (case-insensitive).
    Tries to match first_name + last_name, first_name only, or last_name only.
    """
    cleaned = clean_doctor_name(name)
    if not cleaned:
        return None

    # Split into parts
    parts = cleaned.split()
    if len(parts) >= 2:
        # Try full name match
        doctor = db.query(Doctor).filter(
            func.concat(Doctor.first_name, ' ', Doctor.last_name).ilike(f"%{cleaned}%")
        ).first()
        if doctor:
            return doctor
        # Try first and last separately
        first, last = parts[0], parts[-1]
        doctor = db.query(Doctor).filter(
            Doctor.first_name.ilike(f"%{first}%"),
            Doctor.last_name.ilike(f"%{last}%")
        ).first()
        if doctor:
            return doctor
    else:
        # Single word: search in first_name or last_name
        doctor = db.query(Doctor).filter(
            Doctor.first_name.ilike(f"%{cleaned}%") | Doctor.last_name.ilike(f"%{cleaned}%")
        ).first()
        if doctor:
            return doctor
    return None

def book_appointment(db: Session, doctor_name: str, patient_id: int, date_expr: str, time_expr: str) -> dict:
    """
    Attempt to book an appointment.
    """
    logger.info(f"Booking attempt: doctor='{doctor_name}', patient={patient_id}, date='{date_expr}', time='{time_expr}'")

    # 1. Find doctor
    doctor = find_doctor_by_name(db, doctor_name)
    if not doctor:
        return {
            "success": False,
            "message": f"Could not find a doctor matching '{doctor_name}'. Please check the name and try again."
        }

    # 2. Parse date
    if not date_expr:
        return {"success": False, "message": "Please specify a date for the appointment."}
    date = parse_date_expression(date_expr)
    if not date:
        return {"success": False, "message": f"Could not understand the date '{date_expr}'. Please provide a clear date like 'tomorrow' or 'YYYY-MM-DD'."}

    # 3. Parse time
    if not time_expr:
        return {"success": False, "message": "Please specify a time for the appointment."}
    time_range = parse_time_expression(time_expr)
    if not time_range:
        return {"success": False, "message": f"Could not understand the time '{time_expr}'. Please provide a time like 'morning' or '10am'."}
    start_hour, end_hour = time_range

    # 4. Check availability
    day_of_week = date.weekday()
    working_hours = get_doctor_working_hours(doctor.id, day_of_week, db)
    if not working_hours:
        return {"success": False, "message": f"Dr. {doctor.first_name} {doctor.last_name} is not working on {date.strftime('%A')}."}

    # 5. Get free slots in the preferred time range
    free_slots = get_available_slots(doctor.id, date, db, preferred_time_range=(start_hour, end_hour))
    if not free_slots:
        return {"success": False, "message": f"No available slots for Dr. {doctor.first_name} {doctor.last_name} on {date.strftime('%Y-%m-%d')} at that time. Please choose another time or date."}

    # 6. Pick the first available slot
    slot_str = free_slots[0]
    slot_time = datetime.strptime(slot_str, "%I:%M %p").time()
    appointment_datetime = datetime.combine(date, slot_time)

    # 7. Insert appointment
    try:
        new_appointment = Appointment(
            doctor_id=doctor.id,
            patient_id=patient_id,
            appointment_time=appointment_datetime,
            status="scheduled"
        )
        db.add(new_appointment)
        db.commit()
        db.refresh(new_appointment)
        return {
            "success": True,
            "message": f"Appointment booked successfully with Dr. {doctor.first_name} {doctor.last_name} on {appointment_datetime.strftime('%Y-%m-%d at %I:%M %p')}.",
            "appointment_id": new_appointment.id,
            "doctor_name": f"{doctor.first_name} {doctor.last_name}",
            "date": appointment_datetime.strftime("%Y-%m-%d"),
            "time": appointment_datetime.strftime("%I:%M %p")
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Booking insertion failed: {e}")
        return {"success": False, "message": "An error occurred while booking. Please try again later."}
