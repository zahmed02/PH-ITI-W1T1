from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import Appointment, DoctorAvailability


def parse_iso_date(date_str: str):
    """Convert ISO date string to datetime.date, or return None."""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def python_weekday_to_db_day(python_weekday: int) -> int:
    """
    Convert Python's date.weekday() (Monday=0 ... Sunday=6) to the
    database's day_of_week convention.

    The doctor_availability table stores day_of_week with a
    CHECK (day_of_week BETWEEN 0 AND 6) constraint, and the actual data
    uses 1=Monday ... 5=Friday. That only lines up with a
    Sunday=0 ... Saturday=6 convention (a 1=Monday...7=Sunday scheme
    would violate the CHECK constraint on Sundays). So:

        Python Monday(0)   -> DB 1
        Python Tuesday(1)  -> DB 2
        ...
        Python Saturday(5) -> DB 6
        Python Sunday(6)   -> DB 0   <-- NOT 7

    The previous implementation did `day_of_week + 1` with no wraparound,
    which produced 7 for Sunday - an invalid/nonexistent value - so
    Sunday availability lookups always silently failed.
    """
    return (python_weekday + 1) % 7


def get_doctor_working_hours(doctor_id: int, day_of_week: int, db: Session):
    """
    day_of_week: Python's weekday (0=Monday, 6=Sunday). Converted internally
    to the database's day numbering.
    """
    db_day = python_weekday_to_db_day(day_of_week)
    avail = db.query(DoctorAvailability).filter(
        DoctorAvailability.doctor_id == doctor_id,
        DoctorAvailability.day_of_week == db_day
    ).first()
    if not avail:
        return None
    return (avail.start_time, avail.end_time)


def _compute_free_slots(doctor_id: int, date, db: Session, slot_duration: int,
                         preferred_time_range: tuple = None):
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

    if not slots:
        return []

    booked = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_time >= start_dt,
        Appointment.appointment_time < end_dt,
        Appointment.status != "cancelled",
    ).all()
    booked_times = {app.appointment_time for app in booked}

    return [slot for slot in slots if slot not in booked_times]


def get_weekly_availability(doctor_id: int, db: Session, slot_duration: int = 60):
    today = datetime.now().date()
    monday = today - timedelta(days=today.weekday())
    week_days = [monday + timedelta(days=i) for i in range(7)]
    result = {}

    for date in week_days:
        day_name = date.strftime("%A")
        free_slots = _compute_free_slots(doctor_id, date, db, slot_duration)
        result[day_name] = [slot.strftime("%I:%M %p") for slot in free_slots]

    return result


def get_available_slots(doctor_id: int, date_input, db: Session,
                         preferred_time_range: tuple = None, slot_duration: int = 60):
    """
    date_input can be a datetime.date, datetime.datetime, or ISO string (YYYY-MM-DD).
    Returns a list of formatted time strings (e.g. "09:00 AM").
    """
    if isinstance(date_input, str):
        date = parse_iso_date(date_input)
        if not date:
            return []
    else:
        date = date_input.date() if hasattr(date_input, 'date') else date_input

    free_slots = _compute_free_slots(doctor_id, date, db, slot_duration, preferred_time_range)
    return [slot.strftime("%I:%M %p") for slot in free_slots]
