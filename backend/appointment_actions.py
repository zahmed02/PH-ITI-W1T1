"""
Doctor-initiated appointment lifecycle actions: cancel, take a day off
(which bulk-cancels any existing bookings that day), and transfer a
cancelled appointment to a same-specialty colleague.

Kept separate from booking.py (which only ever CREATES appointments) so
each file has one clear responsibility.
"""
import logging
from datetime import datetime, date as date_type
from sqlalchemy.orm import Session
from backend.models import Appointment, Doctor, Patient, Notification, DoctorTimeOff, AppointmentTransfer
from backend.availability import get_doctor_working_hours, _compute_free_slots
from backend.email_service import send_appointment_cancellation, send_appointment_confirmation
from backend.booking import build_slip_pdf_for_appointment

logger = logging.getLogger(__name__)


def cancel_appointment(db: Session, appointment: Appointment, reason: str = "") -> dict:
    """Cancels a single appointment and emails the patient (no PDF - a cancellation isn't a slip)."""
    if appointment.status == "cancelled":
        return {"success": False, "message": "That appointment is already cancelled."}

    doctor = db.query(Doctor).filter(Doctor.id == appointment.doctor_id).first()
    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()

    appointment.status = "cancelled"
    db.commit()
    db.refresh(appointment)

    email_sent = False
    if doctor and patient:
        email_sent = send_appointment_cancellation(patient, doctor, appointment, reason)

    return {
        "success": True,
        "message": "Appointment cancelled.",
        "appointment_id": appointment.id,
        "cancellation_email_sent": email_sent,
    }


def set_doctor_day_off(db: Session, doctor_id: int, off_date: date_type, reason: str = "") -> dict:
    """
    Marks a doctor unavailable for one specific date (blocking future
    bookings via availability.py) AND cancels every existing scheduled
    appointment that doctor has on that date, emailing each affected
    patient. Returns the list of cancelled appointment ids so the caller
    (frontend) can immediately offer to transfer each one to a colleague.
    """
    existing = db.query(DoctorTimeOff).filter(
        DoctorTimeOff.doctor_id == doctor_id,
        DoctorTimeOff.off_date == off_date,
    ).first()
    if existing:
        return {"success": False, "message": "That date is already marked as a day off."}

    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        return {"success": False, "message": "Doctor not found."}

    day_start = datetime.combine(off_date, datetime.min.time())
    day_end = datetime.combine(off_date, datetime.max.time())

    affected = db.query(Appointment).filter(
        Appointment.doctor_id == doctor_id,
        Appointment.appointment_time >= day_start,
        Appointment.appointment_time <= day_end,
        Appointment.status == "scheduled",
    ).all()

    db.add(DoctorTimeOff(doctor_id=doctor_id, off_date=off_date, reason=reason))
    db.commit()

    cancelled_ids = []
    for appt in affected:
        result = cancel_appointment(db, appt, reason=reason or f"Dr. {doctor.last_name} is unavailable that day.")
        if result["success"]:
            cancelled_ids.append(appt.id)

    return {
        "success": True,
        "message": f"{off_date.isoformat()} marked as a day off. {len(cancelled_ids)} existing appointment(s) were cancelled and their patients notified.",
        "cancelled_appointment_ids": cancelled_ids,
    }


def propose_transfer(db: Session, appointment: Appointment, from_doctor: Doctor, to_doctor_id: int) -> dict:
    """
    Doctor A proposes moving a (now-cancelled) appointment's patient to
    Doctor B. Nothing about the appointment/slot changes yet - this just
    creates a pending request and notifies Doctor B. Doctor B must
    manually confirm (see confirm_transfer) before anything actually
    books.
    """
    if appointment.status != "cancelled":
        return {"success": False, "message": "Only a cancelled appointment can be transferred."}

    to_doctor = db.query(Doctor).filter(Doctor.id == to_doctor_id).first()
    if not to_doctor:
        return {"success": False, "message": "Target doctor not found."}
    if to_doctor.id == from_doctor.id:
        return {"success": False, "message": "Cannot transfer an appointment to yourself."}
    if to_doctor.specialty != from_doctor.specialty:
        return {"success": False, "message": f"{to_doctor.first_name} {to_doctor.last_name} is not in the same department ({from_doctor.specialty})."}

    existing_pending = db.query(AppointmentTransfer).filter(
        AppointmentTransfer.appointment_id == appointment.id,
        AppointmentTransfer.status == "pending",
    ).first()
    if existing_pending:
        return {"success": False, "message": "A transfer for this appointment is already pending."}

    patient = db.query(Patient).filter(Patient.id == appointment.patient_id).first()

    transfer = AppointmentTransfer(
        appointment_id=appointment.id,
        from_doctor_id=from_doctor.id,
        to_doctor_id=to_doctor.id,
        status="pending",
    )
    db.add(transfer)
    db.flush()

    db.add(Notification(
        doctor_id=to_doctor.id,
        appointment_id=appointment.id,
        message=(
            f"Dr. {from_doctor.first_name} {from_doctor.last_name} wants to transfer "
            f"{patient.first_name} {patient.last_name}'s appointment on "
            f"{appointment.appointment_time.strftime('%A, %Y-%m-%d')} at "
            f"{appointment.appointment_time.strftime('%I:%M %p')} to you. "
            f"Review it under Appointment Slips / Transfers."
        ),
    ))
    db.commit()
    db.refresh(transfer)

    return {"success": True, "message": f"Transfer proposed to Dr. {to_doctor.first_name} {to_doctor.last_name}.", "transfer_id": transfer.id}


def confirm_transfer(db: Session, transfer: AppointmentTransfer) -> dict:
    """
    The receiving doctor confirms they'll take the patient. Re-checks
    availability at THIS moment (their schedule may have changed since
    the transfer was proposed) - if the slot is no longer free, the
    confirm fails cleanly rather than silently double-booking. Only on
    success does a new Appointment get created and the patient emailed
    the new PDF slip.
    """
    if transfer.status != "pending":
        return {"success": False, "message": f"This transfer is already {transfer.status}."}

    original = db.query(Appointment).filter(Appointment.id == transfer.appointment_id).first()
    to_doctor = db.query(Doctor).filter(Doctor.id == transfer.to_doctor_id).first()
    patient = db.query(Patient).filter(Patient.id == original.patient_id).first() if original else None
    if not original or not to_doctor or not patient:
        return {"success": False, "message": "Related record not found."}

    slot_date = original.appointment_time.date()
    working = get_doctor_working_hours(to_doctor.id, slot_date, db)
    if not working:
        return {"success": False, "message": f"You are not working on {slot_date.strftime('%A, %Y-%m-%d')} - cannot confirm this transfer."}

    free_slots = _compute_free_slots(to_doctor.id, slot_date, db, slot_duration=60)
    if original.appointment_time not in free_slots:
        return {"success": False, "message": "That time is no longer free on your schedule - cannot confirm this transfer."}

    new_appointment = Appointment(
        doctor_id=to_doctor.id,
        patient_id=patient.id,
        appointment_time=original.appointment_time,
        status="scheduled",
    )
    db.add(new_appointment)
    db.flush()

    db.add(Notification(
        doctor_id=to_doctor.id,
        appointment_id=new_appointment.id,
        message=(
            f"Transfer confirmed: {patient.first_name} {patient.last_name} is now booked with you on "
            f"{new_appointment.appointment_time.strftime('%A, %Y-%m-%d')} at "
            f"{new_appointment.appointment_time.strftime('%I:%M %p')}."
        ),
    ))

    transfer.status = "confirmed"
    transfer.new_appointment_id = new_appointment.id
    transfer.resolved_at = datetime.now()
    db.commit()
    db.refresh(new_appointment)

    pdf_bytes = build_slip_pdf_for_appointment(db, new_appointment, to_doctor, patient)
    email_sent = send_appointment_confirmation(patient, to_doctor, pdf_bytes)

    return {
        "success": True,
        "message": f"Transfer confirmed - {patient.first_name} {patient.last_name} is now booked with you.",
        "new_appointment_id": new_appointment.id,
        "confirmation_email_sent": email_sent,
    }


def decline_transfer(db: Session, transfer: AppointmentTransfer) -> dict:
    if transfer.status != "pending":
        return {"success": False, "message": f"This transfer is already {transfer.status}."}

    from_doctor = db.query(Doctor).filter(Doctor.id == transfer.from_doctor_id).first()
    to_doctor = db.query(Doctor).filter(Doctor.id == transfer.to_doctor_id).first()

    transfer.status = "declined"
    transfer.resolved_at = datetime.now()

    if from_doctor and to_doctor:
        db.add(Notification(
            doctor_id=from_doctor.id,
            appointment_id=transfer.appointment_id,
            message=f"Dr. {to_doctor.first_name} {to_doctor.last_name} was unable to accept your transferred patient - please choose another doctor.",
        ))

    db.commit()
    return {"success": True, "message": "Transfer declined."}