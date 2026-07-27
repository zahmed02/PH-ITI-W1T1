"""
Sends appointment confirmation emails to patients.

Uses Python's built-in smtplib/email modules (no extra dependency).
Configure via environment variables (add these to .env):

    SMTP_HOST=smtp.gmail.com          (default if unset)
    SMTP_PORT=587                     (default if unset)
    SMTP_USERNAME=your-email@gmail.com
    SMTP_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx   (a Gmail "app password", NOT your normal password)
    SMTP_FROM_EMAIL=your-email@gmail.com    (defaults to SMTP_USERNAME if unset)
    SMTP_FROM_NAME=Stellaris General Hospital

To generate a Gmail app password: your Google Account -> Security ->
2-Step Verification must be ON -> App passwords -> create one for "Mail".

If SMTP_USERNAME/SMTP_APP_PASSWORD aren't set, sending is skipped with a
logged warning instead of raising - a booking must NEVER fail just
because email isn't configured yet.
"""
import os
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
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


def build_confirmation_email(patient, doctor, appointment) -> tuple[str, str]:
    """
    Pure function (no I/O) so the content can be unit-tested without a
    network connection. Returns (subject, plain_text_body).
    """
    day_name = appointment.appointment_time.strftime("%A")
    date_str = appointment.appointment_time.strftime("%Y-%m-%d")
    time_str = appointment.appointment_time.strftime("%I:%M %p")

    subject = f"Appointment Confirmed with Dr. {doctor.last_name} - Stellaris General Hospital"

    body = f"""Hello {patient.first_name},

Your appointment has been successfully booked.

  Doctor:        Dr. {doctor.first_name} {doctor.last_name} (Doctor ID: {doctor.id})
  Specialty:     {doctor.specialty}
  Date:          {day_name}, {date_str}
  Time:          {time_str}
  Patient ID:    {patient.id}
  Appointment ID: {appointment.id}

Please arrive a few minutes early. If you need to cancel or reschedule,
you can do so from your patient portal.

Stellaris General Hospital
This is an automated confirmation - please do not reply to this email.
"""
    return subject, body


def send_email(to_email: str, subject: str, body: str) -> bool:
    """
    Returns True if the email was sent, False if sending was skipped or
    failed. Never raises - a failed/unconfigured email must not break the
    caller's booking flow.
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

        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, [to_email], msg.as_string())

        logger.info(f"Sent confirmation email to {to_email}: {subject}")
        return True
    except Exception:
        logger.exception(f"Failed to send confirmation email to {to_email}")
        return False


def send_appointment_confirmation(patient, doctor, appointment) -> bool:
    subject, body = build_confirmation_email(patient, doctor, appointment)
    return send_email(patient.email, subject, body)