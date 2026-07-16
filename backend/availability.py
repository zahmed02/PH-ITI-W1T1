from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import Appointment

def get_available_slots(doctor_id: int, date: datetime, db: Session, slot_duration: int = 60):
    """
    Return a list of available time slots (strings) for a doctor on a given date.
    Assumes working hours 9:00 - 17:00, slots every 60 minutes.
    Returns empty list if no slots available.
    """
    if not date:
        return []
    
    # Set to start of day if time is not set
    date = date.replace(hour=9, minute=0, second=0, microsecond=0)
    
    # Generate all possible slots for that day (9:00 to 16:00)
    start = date.replace(hour=9, minute=0, second=0, microsecond=0)
    end = date.replace(hour=17, minute=0, second=0, microsecond=0)
    
    # If the date is in the past, return empty
    if start < datetime.now().replace(hour=0, minute=0, second=0, microsecond=0):
        return []
    
    slots = []
    current = start
    while current + timedelta(minutes=slot_duration) <= end:
        slots.append(current)
        current += timedelta(minutes=slot_duration)
    
    # Get booked slots from appointments
    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_time >= start,
        Appointment.appointment_time < end
    ).all()
    booked_times = [app.appointment_time for app in booked]
    
    # Free slots are those not in booked_times
    free = []
    for slot in slots:
        if slot not in booked_times:
            free.append(slot.strftime("%I:%M %p"))
    
    return free