from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
from backend.models import Doctor, Appointment
from backend.availability import get_available_slots, get_doctor_working_hours
import logging

logger = logging.getLogger(__name__)

def book_appointment(db: Session, doctor_name: str, patient_id: int, date_expr: str, time_expr: str) -> dict:
    """
    date_expr: ISO date string (YYYY-MM-DD)
    time_expr: time string in HH:MM (24-hour)
    """
    # Find doctor
    doctor = db.query(Doctor).filter(
        func.concat(Doctor.first_name, ' ', Doctor.last_name).ilike(f"%{doctor_name}%")
    ).first()
    if not doctor:
        return {"success": False, "message": f"Could not find a doctor named '{doctor_name}'."}

    # Parse date and time
    try:
        date_obj = datetime.strptime(date_expr, "%Y-%m-%d").date()
        time_obj = datetime.strptime(time_expr, "%H:%M").time()
        appointment_datetime = datetime.combine(date_obj, time_obj)
    except Exception as e:
        logger.error(f"Date/time parsing failed: {e}")
        return {"success": False, "message": "Could not understand the date or time format. Please use YYYY-MM-DD for date and HH:MM for time."}

    # Check if doctor works that day
    day_of_week = date_obj.weekday()
    working = get_doctor_working_hours(doctor.id, day_of_week, db)
    if not working:
        return {"success": False, "message": f"Dr. {doctor.first_name} {doctor.last_name} is not working on {date_obj.strftime('%A')}."}

    # Check availability
    # We'll check if the specific time is free
    slots = get_available_slots(doctor.id, date_obj, db)
    if appointment_datetime.strftime("%I:%M %p") not in slots:
        return {"success": False, "message": f"The requested time {appointment_datetime.strftime('%I:%M %p')} is not available. Please choose another time."}

    # Create appointment
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