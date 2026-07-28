"""
Human-facing numbering shown on appointment slips (PDF/email) - separate
from the internal database primary key, which stays exactly as-is for all
foreign keys and internal logic. These are purely DISPLAY formats,
computed on demand from existing data.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func, or_, and_
from backend.models import Appointment, Patient


def compute_display_appointment_id(db: Session, appointment: Appointment) -> str:
    """
    Format: dd/mm/doctor_id/n
    where n = this appointment's 1-based position, by time of day, among
    that doctor's non-cancelled appointments on the same date. E.g. the
    doctor's 9:00 AM slot that day is "1", the next one chronologically
    is "2", regardless of booking order.

    Example: "28/07/2/1" = July 28th, Doctor #2, their 1st appointment
    that day.
    """
    date_str = appointment.appointment_time.strftime("%d/%m")
    same_day_start = appointment.appointment_time.replace(hour=0, minute=0, second=0, microsecond=0)
    same_day_end = same_day_start.replace(hour=23, minute=59, second=59)

    earlier_or_equal_count = db.query(func.count(Appointment.id)).filter(
        Appointment.doctor_id == appointment.doctor_id,
        Appointment.appointment_time >= same_day_start,
        Appointment.appointment_time <= same_day_end,
        or_(
            Appointment.appointment_time < appointment.appointment_time,
            and_(Appointment.appointment_time == appointment.appointment_time, Appointment.id <= appointment.id),
        ),
        Appointment.status != "cancelled",
    ).scalar() or 1

    return f"{date_str}/{appointment.doctor_id}/{earlier_or_equal_count}"


def compute_seniority_number(db: Session, appointment: Appointment) -> int:
    """
    Hospital-wide daily queue position: how many appointments (any doctor)
    for the SAME DATE were created at or before this one, i.e. "you were
    the Nth person to book an appointment for this day."

    Uses `id` (not `created_at`) as the creation-order signal: id is a
    monotonically increasing auto-increment key on both SQLite and
    Postgres, so "lower id = created earlier" always holds - unlike
    comparing server-generated timestamps, which can tie at low
    resolution and are prone to string-formatting mismatches on SQLite
    between a stored default and a later bound comparison value.
    """
    same_day_start = appointment.appointment_time.replace(hour=0, minute=0, second=0, microsecond=0)
    same_day_end = same_day_start.replace(hour=23, minute=59, second=59)

    count = db.query(func.count(Appointment.id)).filter(
        Appointment.appointment_time >= same_day_start,
        Appointment.appointment_time <= same_day_end,
        Appointment.id <= appointment.id,
        Appointment.status != "cancelled",
    ).scalar() or 1

    return count


def compute_mr_number(patient: Patient) -> str:
    """
    A stable "Medical Record Number" derived entirely from data the
    patient record already has - no new DB field needed, and it never
    changes for a given patient. Format: {patient_id:03d}-{reg_month:02d}-{reg_year_2digit}
    Example: patient #18, registered July 2026 -> "018-07-26"
    """
    created = patient.created_at
    return f"{patient.id:03d}-{created.month:02d}-{created.year % 100:02d}"