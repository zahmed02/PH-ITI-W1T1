"""
Generates the appointment slip PDF attached to confirmation emails.

Deliberately takes plain strings/values only (no DB session, no ORM
objects) - all the numbering/lookup work happens in
backend/appointment_numbering.py and the caller (booking.py /
appointment_actions.py). That keeps this module pure and easy to test:
give it the same inputs, get the same PDF, no database required.
"""
import os
import io
import logging
from reportlab.lib.pagesizes import A5
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

logger = logging.getLogger(__name__)

HOSPITAL_NAME = os.getenv("HOSPITAL_NAME", "Stellaris General Hospital")
HOSPITAL_ADDRESS = os.getenv("HOSPITAL_ADDRESS", "123 Wellness Avenue, Karachi.")
HOSPITAL_PHONE = os.getenv("HOSPITAL_PHONE", "Ph: 021-3498-0000")
HOSPITAL_EMAIL = os.getenv("HOSPITAL_EMAIL", "info@stellaris-hospital.org")
HOSPITAL_WEBSITE = os.getenv("HOSPITAL_WEBSITE", "stellaris-hospital.org")

# Looked up relative to the project root at runtime (same convention as
# main.py's static file mount). Missing/unreadable logo -> the header
# falls back to the hospital name as text only, it never crashes the PDF.
_DEFAULT_LOGO_PATH = os.path.join(os.path.dirname(__file__), "..", "static", "images", "logo.png")
HOSPITAL_LOGO_PATH = os.getenv("HOSPITAL_LOGO_PATH", _DEFAULT_LOGO_PATH)

PRIMARY_COLOR = HexColor("#00478d")
MUTED_COLOR = HexColor("#5a6472")
LINE_COLOR = HexColor("#c9ced6")


def _draw_header(c: canvas.Canvas, width: float, y: float) -> float:
    margin = 14 * mm
    logo_drawn = False

    if HOSPITAL_LOGO_PATH and os.path.isfile(HOSPITAL_LOGO_PATH):
        try:
            c.drawImage(
                HOSPITAL_LOGO_PATH, margin, y - 18 * mm,
                width=18 * mm, height=18 * mm,
                preserveAspectRatio=True, mask="auto",
            )
            logo_drawn = True
        except Exception:
            logger.warning(f"Could not draw logo at {HOSPITAL_LOGO_PATH}, falling back to text header", exc_info=True)

    text_x = margin + (22 * mm if logo_drawn else 0)

    c.setFont("Helvetica-Bold", 15)
    c.setFillColor(PRIMARY_COLOR)
    c.drawString(text_x, y - 6 * mm, HOSPITAL_NAME)

    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED_COLOR)
    c.drawString(text_x, y - 11 * mm, HOSPITAL_ADDRESS)
    c.drawString(text_x, y - 15 * mm, f"{HOSPITAL_PHONE}   E-mail: {HOSPITAL_EMAIL}")
    c.drawString(text_x, y - 19 * mm, f"Website: {HOSPITAL_WEBSITE}")

    return y - 24 * mm


def _draw_field_row(c: canvas.Canvas, x: float, y: float, label: str, value: str) -> float:
    c.setFont("Helvetica", 9)
    c.setFillColor(MUTED_COLOR)
    c.drawString(x, y, label)
    c.setFont("Helvetica-Bold", 9)
    c.setFillColor(HexColor("#1a1a1a"))
    c.drawString(x + 42 * mm, y, value)
    return y - 6.5 * mm


def generate_appointment_slip_pdf(
    *,
    doctor_name: str,
    department: str,
    patient_name: str,
    appointment_date_str: str,
    appointment_time_str: str,
    day_name: str,
    seniority_no: int,
    mr_no: str,
    display_appointment_id: str,
    booking_date_str: str,
    printed_at_str: str,
    status_label: str = "Temporary Appointment Slip",
    footer_note: str = "Thank you for choosing us. Please arrive 15 minutes early.",
) -> bytes:
    """Returns the finished PDF as raw bytes, ready to attach to an email."""
    buffer = io.BytesIO()
    page_width, page_height = A5
    c = canvas.Canvas(buffer, pagesize=A5)

    margin = 14 * mm
    y = page_height - 12 * mm

    y = _draw_header(c, page_width, y)

    c.setStrokeColor(LINE_COLOR)
    c.setLineWidth(0.75)
    c.line(margin, y, page_width - margin, y)
    y -= 6 * mm

    c.setFont("Helvetica", 7.5)
    c.setFillColor(MUTED_COLOR)
    c.drawRightString(page_width - margin, page_height - 8 * mm, f"Printed: {printed_at_str}")

    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(PRIMARY_COLOR)
    c.drawCentredString(page_width / 2, y, status_label)
    y -= 9 * mm

    c.setStrokeColor(LINE_COLOR)
    c.rect(margin, y - 58 * mm, page_width - 2 * margin, 58 * mm, stroke=1, fill=0)
    inner_y = y - 6 * mm
    inner_x = margin + 5 * mm

    inner_y = _draw_field_row(c, inner_x, inner_y, "Appointment Date:", f"{appointment_date_str} ({day_name})")
    inner_y = _draw_field_row(c, inner_x, inner_y, "Appointment Time:", appointment_time_str)
    inner_y = _draw_field_row(c, inner_x, inner_y, "Appointment ID:", display_appointment_id)
    inner_y = _draw_field_row(c, inner_x, inner_y, "Seniority No:", str(seniority_no))
    inner_y = _draw_field_row(c, inner_x, inner_y, "MR NO:", mr_no)
    inner_y -= 1 * mm
    c.setStrokeColor(LINE_COLOR)
    c.line(inner_x, inner_y, page_width - margin - 5 * mm, inner_y)
    inner_y -= 5 * mm
    inner_y = _draw_field_row(c, inner_x, inner_y, "Patient Name:", patient_name.upper())
    inner_y = _draw_field_row(c, inner_x, inner_y, "Consultant:", doctor_name.upper())
    inner_y = _draw_field_row(c, inner_x, inner_y, "Department:", department)
    inner_y = _draw_field_row(c, inner_x, inner_y, "Booking Date:", booking_date_str)

    y = y - 58 * mm - 10 * mm

    c.setStrokeColor(LINE_COLOR)
    c.line(margin, y, page_width - margin, y)
    y -= 6 * mm

    c.setFont("Helvetica-Oblique", 8)
    c.setFillColor(MUTED_COLOR)
    c.drawCentredString(page_width / 2, y, footer_note)
    y -= 5 * mm
    c.setFont("Helvetica", 7)
    c.drawCentredString(page_width / 2, y, "This is a computer-generated document and does not require a signature.")

    c.showPage()
    c.save()
    return buffer.getvalue()
