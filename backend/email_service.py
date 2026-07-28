"""
Sends appointment-related emails to patients.

Uses Python's built-in smtplib/email modules (no extra dependency for
sending - PDF generation itself uses reportlab, see backend/pdf_service.py).
Configure via environment variables (add these to .env):

    SMTP_HOST=smtp.gmail.com          (default if unset)
    SMTP_PORT=587                     (default if unset)
    SMTP_USERNAME=your-email@gmail.com
    SMTP_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx   (a Gmail "app password", NOT your normal password)
    SMTP_FROM_EMAIL=your-email@gmail.com    (defaults to SMTP_USERNAME if unset)
    SMTP_FROM_NAME=Stellaris General Hospital

If SMTP_USERNAME/SMTP_APP_PASSWORD aren't set, sending is skipped with a
logged warning instead of raising - a booking/cancellation must NEVER
fail just because email isn't configured yet.
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_APP_PASSWORD = os.getenv("SMTP_APP_PASSWORD")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", SMTP_USERNAME)
SMTP_FROM_NAME = os.getenv("SMTP_FROM_NAME", "Stellaris General Hospital")


def is_email_configured() -> bool:
    return bool(SMTP_USERNAME and SMTP_APP_PASSWORD)


def build_confirmation_email_text(patient_first_name: str, doctor_last_name: str) -> tuple[str, str]:
    """
    Short email body - the real details (doctor, department, date, time,
    seniority/MR numbers) live in the attached PDF slip, not the email
    body, per the hospital's requested format.
    """
    subject = f"Appointment Confirmed with Dr. {doctor_last_name} - {SMTP_FROM_NAME}"
    body = f"""Hello {patient_first_name},

Your appointment has been successfully booked. Your appointment slip is
attached to this email as a PDF - please keep it for your records and
bring it (printed or on your phone) to your visit.

Please arrive a few minutes early. If you need to cancel or reschedule,
you can do so from your patient portal.

{SMTP_FROM_NAME}
This is an automated confirmation - please do not reply to this email.
"""
    return subject, body


def build_cancellation_email(patient_first_name: str, doctor_last_name: str, day_name: str, date_str: str, time_str: str, reason: str = "") -> tuple[str, str]:
    subject = f"Appointment Cancelled - {SMTP_FROM_NAME}"
    reason_line = f"\nReason: {reason}\n" if reason else ""
    body = f"""Hello {patient_first_name},

Your appointment with Dr. {doctor_last_name} on {day_name}, {date_str} at {time_str}
has been cancelled.
{reason_line}
Please contact us or use your patient portal to book a new appointment
if you still need to be seen.

We apologize for any inconvenience.

{SMTP_FROM_NAME}
This is an automated notice - please do not reply to this email.
"""
    return subject, body


def send_email(to_email: str, subject: str, body: str, pdf_attachment: bytes = None, pdf_filename: str = "appointment_slip.pdf") -> bool:
    """
    Returns True if the email was sent, False if sending was skipped or
    failed. Never raises - a failed/unconfigured email must not break the
    caller's booking/cancellation flow.
    """
    if not is_email_configured():
        logger.warning(
            "Email not sent (SMTP_USERNAME/SMTP_APP_PASSWORD not set in .env) - "
            f"would have sent '{subject}' to {to_email}."
        )
        return False

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{SMTP_FROM_NAME} <{SMTP_FROM_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        if pdf_attachment:
            part = MIMEApplication(pdf_attachment, _subtype="pdf")
            part.add_header("Content-Disposition", "attachment", filename=pdf_filename)
            msg.attach(part)

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, [to_email], msg.as_string())

        logger.info(f"Sent email to {to_email}: {subject}" + (" (with PDF attachment)" if pdf_attachment else ""))
        return True
    except Exception:
        logger.exception(f"Failed to send email to {to_email}")
        return False


def send_appointment_confirmation(patient, doctor, pdf_bytes: bytes) -> bool:
    subject, body = build_confirmation_email_text(patient.first_name, doctor.last_name)
    filename = f"appointment_slip_{patient.last_name}.pdf".replace(" ", "_")
    return send_email(patient.email, subject, body, pdf_attachment=pdf_bytes, pdf_filename=filename)


def send_appointment_cancellation(patient, doctor, appointment, reason: str = "") -> bool:
    day_name = appointment.appointment_time.strftime("%A")
    date_str = appointment.appointment_time.strftime("%d-%b-%y")
    time_str = appointment.appointment_time.strftime("%I:%M %p")
    subject, body = build_cancellation_email(patient.first_name, doctor.last_name, day_name, date_str, time_str, reason)
    return send_email(patient.email, subject, body)  # no PDF for a cancellation