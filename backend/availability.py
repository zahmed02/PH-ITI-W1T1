from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import Appointment, DoctorAvailability

def parse_iso_date(date_str: str):
    """Convert ISO date string to datetime.date, or return None."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except:
        return None

def get_doctor_working_hours(doctor_id: int, day_of_week: int, db: Session):
    """
    day_of_week: Python's weekday (0=Monday, 6=Sunday)
    Database uses 1=Monday, 2=Tuesday, ..., 7=Sunday.
    """
    db_day = day_of_week + 1  # Convert to database format
    avail = db.query(DoctorAvailability).filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.day_of_week == db_day
    ).first()
    if not avail:
        return None
    return (avail.start_time, avail.end_time)

def get_weekly_availability(doctor_id: int, db: Session, slot_duration: int = 60):
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]
    result = {}

    for date in week_days:
        day_name = date.strftime("%A")
        day_of_week = date.weekday()
        working = get_doctor_working_hours(doctor_id, day_of_week, db)
        if not working:
            result[day_name] = []
            continue
        start_time, end_time = working
        start_dt = datetime.combine(date, start_time)
        end_dt = datetime.combine(date, end_time)

        slots = []
        current = start_dt
        while current + timedelta(minutes=slot_duration) <= end_dt:
            slots.append(current)
            current += timedelta(minutes=slot_duration)

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
        result[day_name] = free
    return result

def get_available_slots(doctor_id: int, date_input, db: Session, preferred_time_range: tuple = None, slot_duration: int = 60):
    """
    date_input can be a datetime.date, datetime.datetime, or ISO string (YYYY-MM-DD).
    """
    if isinstance(date_input, str):
        date = parse_iso_date(date_input)
        if not date:
            return []
    else:
        date = date_input.date() if hasattr(date_input, 'date') else date_input

    day_of_week = date.weekday()
    working = get_doctor_working_hours(doctor_id, day_of_week, db)
    if not working:
        return []
    start_time, end_time = working
    start_dt = datetime.combine(date, start_time)
    end_dt = datetime.combine(date, end_time)

    if preferred_time_range:
        pref_start_hour, pref_end_hour = preferred_time_range
        pref_start = start_dt.replace(hour=pref_start_hour, minute=0)
        pref_end = start_dt.replace(hour=pref_end_hour, minute=0)
        effective_start = max(start_dt, pref_start)
        effective_end = min(end_dt, pref_end)
        if effective_start >= effective_end:
            return []
        start_dt, end_dt = effective_start, effective_end

    slots = []
    current = start_dt
    while current + timedelta(minutes=slot_duration) <= end_dt:
        slots.append(current)
        current += timedelta(minutes=slot_duration)

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