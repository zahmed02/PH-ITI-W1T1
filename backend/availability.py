from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import Appointment, DoctorAvailability

def get_doctor_working_hours(doctor_id: int, day_of_week: int, db: Session):
    """
    Returns (start_time, end_time) for the given doctor on that day_of_week,
    or None if the doctor is not working that day.
    """
    avail = db.query(DoctorAvailability).filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.day_of_week == day_of_week
    ).first()
    if not avail:
        return None
    return (avail.start_time, avail.end_time)

def get_available_slots(
    doctor_id: int,
    date: datetime,
    db: Session,
    preferred_time_range: tuple[int, int] = None,
    slot_duration: int = 60
) -> list[str]:
    """
    Return available time slots (formatted strings) for a doctor on a given date.
    Uses the doctor's actual working hours from doctor_availability.
    If preferred_time_range (start_hour, end_hour) is given, restrict slots to that window.
    """
    if not date:
        return []
    
    day_of_week = date.weekday()  # Monday=0, Sunday=6
    working_hours = get_doctor_working_hours(doctor_id, day_of_week, db)
    if not working_hours:
        return []  # doctor not working that day
    
    start_time, end_time = working_hours
    # Convert to datetime objects on the given date
    start_dt = datetime.combine(date, start_time)
    end_dt = datetime.combine(date, end_time)
    
    # If date is in the past, return empty
    if start_dt < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
        return []
    
    # Apply preferred time range if given
    if preferred_time_range:
        pref_start_hour, pref_end_hour = preferred_time_range
        pref_start = start_dt.replace(hour=pref_start_hour, minute=0)
        pref_end = start_dt.replace(hour=pref_end_hour, minute=0)
        effective_start = max(start_dt, pref_start)
        effective_end = min(end_dt, pref_end)
        if effective_start >= effective_end:
            return []
        start_dt, end_dt = effective_start, effective_end
    
    # Generate slots
    slots = []
    current = start_dt
    while current + timedelta(minutes=slot_duration) <= end_dt:
        slots.append(current)
        current += timedelta(minutes=slot_duration)
    
    # Get booked appointments for that doctor on that day
    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_time >= start_dt,
        Appointment.appointment_time < end_dt
    ).all()
    booked_times = [app.appointment_time for app in booked]
    
    free = []
    for slot in slots:
        if slot not in booked_times:
            free.append(slot.strftime("%I:%M %p"))
    
    return free