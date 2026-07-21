from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import json
import logging
import time

from backend.database import get_db
from backend.models import Doctor, Review, Appointment, Patient
from backend.llm_helpers import client, detect_language
from backend.availability import get_available_slots
from backend.session_store import session_store
from backend.booking import book_appointment

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

# ---- Global cache ----
_global_availability_cache = None
_global_cache_timestamp = 0
_global_cache_booking_flag = False

def build_global_availability(db: Session) -> str:
    global _global_availability_cache, _global_cache_timestamp
    doctors = db.query(Doctor).all()
    today = datetime.now().date()
    days_range = 3
    week_days = [today + timedelta(days=i) for i in range(days_range)]
    lines = []
    for doc in doctors:
        avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doc.id).scalar() or 0.0
        date_slots = []
        for day in week_days:
            date_str = day.strftime("%Y-%m-%d")
            slots = get_available_slots(doc.id, date_str, db)
            if slots:
                hours = []
                for s in slots:
                    parts = s.split()
                    t = parts[0]
                    ampm = parts[1] if len(parts) > 1 else 'AM'
                    h, m = map(int, t.split(':'))
                    if ampm == 'PM' and h != 12:
                        h += 12
                    elif ampm == 'AM' and h == 12:
                        h = 0
                    hours.append(str(h))
                date_slots.append(f"{date_str}:{','.join(hours)}")
            else:
                date_slots.append(f"{date_str}:-")
        lines.append(
            f"{doc.first_name} {doc.last_name} ({doc.specialty}, {doc.years_of_experience}y, {float(avg_rating):.1f}): "
            + " ".join(date_slots)
        )
    result = "\n".join(lines)
    _global_availability_cache = result
    _global_cache_timestamp = time.time()
    return result

def get_availability(db: Session) -> str:
    global _global_availability_cache, _global_cache_timestamp, _global_cache_booking_flag
    if _global_availability_cache is None or (time.time() - _global_cache_timestamp) > 3600 or _global_cache_booking_flag:
        result = build_global_availability(db)
        _global_cache_booking_flag = False
        return result
    return _global_availability_cache

# ---------- Tool definition ----------
booking_tool = {
    "type": "function",
    "function": {
        "name": "book_appointment",
        "description": "Book an appointment for a patient with a doctor",
        "parameters": {
            "type": "object",
            "properties": {
                "doctor_name": {"type": "string", "description": "Full name of the doctor"},
                "patient_id": {"type": "integer", "description": "The patient's ID"},
                "date": {"type": "string", "description": "Date in YYYY-MM-DD format"},
                "time": {"type": "string", "description": "Time in HH:MM (24-hour format)"}
            },
            "required": ["doctor_name", "patient_id", "date", "time"]
        }
    }
}

@router.post("/")
def chat(
    query: str = Query(..., description="User's question"),
    patient_id: int = Query(None, description="Patient ID"),
    session_id: str = Query(None, description="Session ID"),
    db: Session = Depends(get_db)
):
    logger.info(f"Chat: {query}")

    if not session_id:
        session_id = f"p{patient_id or 'guest'}_{datetime.now().timestamp()}"
    session = session_store.get(session_id)
    language = detect_language(query)
    session["language"] = language
    session_store.add_message(session_id, "user", query)

    # ---- Get compact availability ----
    avail_text = get_availability(db)

    # ---- Patient appointments ----
    appointments_text = ""
    if patient_id:
        patient = db.query(Patient).filter(Patient.id == patient_id).first()
        if patient:
            apps = db.query(Appointment).filter(Appointment.patient_id == patient_id).all()
            if apps:
                app_lines = []
                for a in apps:
                    doc = db.query(Doctor).filter(Doctor.id == a.doctor_id).first()
                    app_lines.append(f"{doc.first_name} {doc.last_name} - {a.appointment_time.strftime('%Y-%m-%d %I:%M %p')} ({a.status})")
                appointments_text = "Your appointments:\n" + "\n".join(app_lines)

    # ---- History (last 4 messages) ----
    history = ""
    if session.get("history"):
        last = session["history"][-4:]
        history = "Prev:\n" + "\n".join([f"{'U' if h['role']=='user' else 'A'}: {h['content']}" for h in last])

    # ---- System prompt with strong context instructions ----
    lang_instruction = "Respond in Romanized Urdu if user wrote in Urdu, else English."
    system_prompt = f"""
You are a medical assistant for Stellaris General Hospital.

Data (doctor: specialty, experience, rating, and free hours for next 3 days):
{avail_text}

{appointments_text}

{history}

{lang_instruction}

IMPORTANT RULES:
1. Remember the doctor mentioned in the conversation. Use that doctor's name when answering follow‑up questions.
2. If the user asks "Unke paas kal 10 AM available hai?" – "Unke" refers to the last doctor mentioned. Use that doctor.
3. If the user asks to book, you MUST call the `book_appointment` tool.
4. Before calling the tool, ensure you have: doctor's full name, patient ID (provided as {patient_id if patient_id else 'ask user'}), date (YYYY-MM-DD), and time (HH:MM).
5. If any detail is missing, ask the user for it. For example, if the date is missing, ask "Kis date ko appointment chahiye?"
6. Do not invent doctors or times. Use the data provided.
7. When the user says "Meri kamar ma dard hai", recommend an Orthopedics doctor.
8. Be concise and helpful.
"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": query}
    ]

    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=messages,
            tools=[booking_tool],
            tool_choice="auto",
            temperature=0.7,
            max_tokens=300
        )
        response_message = resp.choices[0].message
        tool_calls = response_message.tool_calls

        if tool_calls:
            tool_call = tool_calls[0]
            if tool_call.function.name == "book_appointment":
                args = json.loads(tool_call.function.arguments)
                logger.info(f"Tool call: {args}")
                doctor_name = args.get("doctor_name")
                pat_id = args.get("patient_id")
                date_str = args.get("date")
                time_str = args.get("time")

                if not pat_id:
                    final = "I need your patient ID. Please provide it."
                else:
                    patient = db.query(Patient).filter(Patient.id == pat_id).first()
                    if not patient:
                        final = f"Patient ID {pat_id} not found. Please register first."
                    else:
                        booking_result = book_appointment(
                            db=db,
                            doctor_name=doctor_name,
                            patient_id=pat_id,
                            date_expr=date_str,
                            time_expr=time_str
                        )
                        if booking_result.get("success"):
                            final = f"Appointment booked with {doctor_name} on {date_str} at {booking_result.get('time')}. ID: {booking_result.get('appointment_id')}"
                            _global_cache_booking_flag = True
                        else:
                            final = booking_result.get("message", "Booking failed. Please check the details.")
        else:
            final = response_message.content.strip()

    except Exception as e:
        logger.error(f"LLM error: {e}")
        final = "I'm having trouble generating a response. Please try again."

    session_store.add_message(session_id, "assistant", final)
    return {"response": final}