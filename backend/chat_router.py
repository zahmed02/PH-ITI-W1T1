from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.models import Appointment, Doctor, Patient, Review
from backend.booking import book_appointment, find_doctors_by_name, clean_doctor_name
from backend.availability import get_available_slots, get_weekly_availability, parse_iso_date
from backend.llm_helpers import get_chat_completion, detect_language
from backend.session_store import session_store
from backend.schemas import ChatRequest, ChatResponse

router = APIRouter(prefix="/chat", tags=["Chat"])
logger = logging.getLogger(__name__)

MAX_TOOL_ITERATIONS = 5


# ==================================================================
# Tool (function) definitions exposed to the LLM.
#
# Instead of guessing intent from keyword lists and pulling dates/times
# out with regex, the model itself decides when it needs real data and
# calls one of these. Every fact it states to the user should come from
# a tool result, not from its own memory - this is what prevents
# hallucinated doctors/times/availability.
# ==================================================================

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_doctors",
            "description": (
                "Search for doctors, optionally filtered by specialty and/or name. "
                "Returns each doctor's specialty, years of experience, average rating, and bio. "
                "Always call this before answering questions about which doctors exist, "
                "their specialties, experience, or ratings - never guess."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "specialty": {"type": "string", "description": "Medical specialty to filter by, e.g. 'Cardiology'."},
                    "name": {"type": "string", "description": "A doctor's first or last name to search for."},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_availability",
            "description": (
                "Get real available appointment slots for a specific doctor. "
                "If a date is given, returns that day's free slots; otherwise returns the "
                "whole current week. Always call this before telling the user a doctor is "
                "available/unavailable at a given time, and before booking."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "The doctor's first and/or last name."},
                    "date": {"type": "string", "description": "ISO date YYYY-MM-DD. Omit to get the whole current week."},
                },
                "required": ["doctor_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "book_appointment",
            "description": (
                "Book an appointment for the current patient with a specific doctor, date, and time. "
                "Only call this after the user has explicitly confirmed all three of: doctor, exact date, "
                "and exact time. If any of these is missing or ambiguous, ask the user instead of calling this."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "The doctor's first and/or last name."},
                    "date": {"type": "string", "description": "ISO date YYYY-MM-DD."},
                    "time": {"type": "string", "description": "24-hour time HH:MM, e.g. '14:00'."},
                },
                "required": ["doctor_name", "date", "time"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_my_appointments",
            "description": "Get the current patient's own appointments (upcoming and past). Use this whenever the user asks about 'my appointments'.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_doctor_reviews",
            "description": "Get patient reviews and rating breakdown for a specific doctor.",
            "parameters": {
                "type": "object",
                "properties": {
                    "doctor_name": {"type": "string", "description": "The doctor's first and/or last name."},
                },
                "required": ["doctor_name"],
            },
        },
    },
]


def _serialize_doctor(doctor: Doctor, db: Session) -> Dict[str, Any]:
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doctor.id).scalar() or 0
    return {
        "id": doctor.id,
        "name": f"Dr. {doctor.first_name} {doctor.last_name}",
        "specialty": doctor.specialty,
        "years_of_experience": doctor.years_of_experience,
        "rating": round(float(avg_rating), 1),
        "bio": doctor.bio or "",
    }


def _tool_search_doctors(db: Session, specialty: Optional[str] = None, name: Optional[str] = None, **_) -> dict:
    query = db.query(Doctor)
    if specialty:
        query = query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    if name:
        clean = clean_doctor_name(name)
        query = query.filter(
            (Doctor.first_name.ilike(f"%{clean}%")) | (Doctor.last_name.ilike(f"%{clean}%"))
        )

    # Compute the true total and the per-specialty breakdown with real
    # aggregate queries, rather than len()'ing a possibly-truncated list.
    # Small models are unreliable at counting/summarizing 10+ items from a
    # raw list - they drop entries and miscount even when the data handed
    # to them was correct. Precomputing the numbers here means the model
    # only has to repeat a value, never count one itself.
    total_count = query.count()

    breakdown_query = db.query(Doctor.specialty, func.count(Doctor.id))
    if specialty:
        breakdown_query = breakdown_query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
    if name:
        clean = clean_doctor_name(name)
        breakdown_query = breakdown_query.filter(
            (Doctor.first_name.ilike(f"%{clean}%")) | (Doctor.last_name.ilike(f"%{clean}%"))
        )
    doctor_count_by_specialty = dict(breakdown_query.group_by(Doctor.specialty).all())

    doctors = query.order_by(Doctor.specialty, Doctor.last_name).limit(50).all()
    if not doctors:
        return {"found": False, "total_count": 0, "specialties": [], "doctor_count_by_specialty": {}, "doctors": []}

    return {
        "found": True,
        "total_count": total_count,
        "specialties": sorted(doctor_count_by_specialty.keys()),
        "doctor_count_by_specialty": doctor_count_by_specialty,
        "doctors": [_serialize_doctor(d, db) for d in doctors],
        "note": (
            "total_count, specialties, and doctor_count_by_specialty above are the "
            "authoritative counts - use them directly for any 'how many' or 'which "
            "departments' question instead of counting the doctors list yourself."
        ),
    }


def _ambiguous_result(doctor_name: str, matches: list) -> dict:
    options = ", ".join(f"Dr. {d.first_name} {d.last_name} ({d.specialty})" for d in matches)
    return {
        "found": False,
        "ambiguous": True,
        "message": f"'{doctor_name}' matches more than one doctor: {options}. Ask the user which one they mean.",
    }


def _tool_get_doctor_availability(db: Session, doctor_name: str, date: Optional[str] = None, **_) -> dict:
    matches = find_doctors_by_name(db, doctor_name)
    if len(matches) == 0:
        return {"found": False, "message": f"No doctor found matching '{doctor_name}'."}
    if len(matches) > 1:
        return _ambiguous_result(doctor_name, matches)
    doctor = matches[0]

    if date:
        parsed = parse_iso_date(date)
        if not parsed:
            return {"found": True, "error": "Invalid date format, expected YYYY-MM-DD."}
        slots = get_available_slots(doctor.id, date, db)
        return {
            "found": True,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "date": date,
            "day_of_week": parsed.strftime("%A"),
            "available_slots": slots,
        }

    weekly = get_weekly_availability(doctor.id, db)
    return {
        "found": True,
        "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
        "weekly_availability": weekly,
    }


def _tool_book_appointment(db: Session, patient_id: int, doctor_name: str, date: str, time: str, **_) -> dict:
    return book_appointment(db, doctor_name, patient_id, date, time)


def _tool_get_my_appointments(db: Session, patient_id: int, **_) -> dict:
    appointments = (
        db.query(Appointment)
        .filter(Appointment.patient_id == patient_id)
        .order_by(Appointment.appointment_time)
        .all()
    )
    if not appointments:
        return {"appointments": []}

    result = []
    for appt in appointments:
        doctor = db.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
        result.append({
            "appointment_id": appt.id,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}" if doctor else "Unknown",
            "date_time": appt.appointment_time.strftime("%Y-%m-%d %I:%M %p"),
            "status": appt.status,
        })
    return {"appointments": result}


def _tool_get_doctor_reviews(db: Session, doctor_name: str, **_) -> dict:
    matches = find_doctors_by_name(db, doctor_name)
    if len(matches) == 0:
        return {"found": False, "message": f"No doctor found matching '{doctor_name}'."}
    if len(matches) > 1:
        return _ambiguous_result(doctor_name, matches)
    doctor = matches[0]

    reviews = (
        db.query(Review)
        .filter(Review.doctor_id == doctor.id)
        .order_by(Review.created_at.desc())
        .limit(10)
        .all()
    )
    avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doctor.id).scalar() or 0
    return {
        "found": True,
        "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
        "average_rating": round(float(avg_rating), 1),
        "review_count": len(reviews),
        "reviews": [{"rating": r.rating, "comment": r.comment or ""} for r in reviews],
    }


TOOL_IMPLEMENTATIONS = {
    "search_doctors": _tool_search_doctors,
    "get_doctor_availability": _tool_get_doctor_availability,
    "book_appointment": _tool_book_appointment,
    "get_my_appointments": _tool_get_my_appointments,
    "get_doctor_reviews": _tool_get_doctor_reviews,
}


def execute_tool_call(name: str, arguments: dict, db: Session, patient_id: int) -> dict:
    impl = TOOL_IMPLEMENTATIONS.get(name)
    if not impl:
        return {"error": f"Unknown tool '{name}'."}
    try:
        return impl(db=db, patient_id=patient_id, **arguments)
    except Exception as e:
        logger.exception(f"Tool '{name}' failed")
        return {"error": f"Something went wrong while running '{name}': {e}"}


def build_system_prompt(language: str) -> str:
    today = datetime.now()
    lang_instruction = {
        "ur": "The user is writing in Urdu script. Respond in Urdu.",
        "en": "Respond in English, unless the user writes in Roman Urdu, in which case respond in Roman Urdu.",
    }.get(language, "Respond in the same language and script the user used.")

    return f"""You are the AI medical assistant for Stellaris General Hospital.

Today's date is {today.strftime('%Y-%m-%d')} ({today.strftime('%A')}).

You have access to tools that query the hospital's real database. You must
use them for any factual claim about doctors, specialties, availability,
ratings, reviews, or appointments - NEVER invent or guess this information.
If a tool returns no results, tell the user honestly instead of making
something up.

When search_doctors returns "total_count", "specialties", or
"doctor_count_by_specialty" fields, use those numbers directly for any
"how many doctors" or "which departments" question. Do NOT count the
entries in the "doctors" list yourself, and do NOT recompute these numbers -
long lists are easy to miscount, so always defer to the precomputed
fields instead.

Before calling book_appointment, you must have the user's explicit
confirmation of the doctor, the exact date, and the exact time. If anything
is missing or ambiguous, ask a clarifying question first instead of calling
the tool speculatively.

If a tool result says a doctor name is ambiguous (matches more than one
doctor), list the specific options it gives you and ask the user to pick
one - never guess which one they meant.

Use the ongoing conversation history to resolve references like "him",
"her", "that doctor", or "unke"/"uska" to whichever doctor was discussed
most recently.

Keep responses concise, warm, and natural. Never mention tools, JSON, or
internal system details to the user.

{lang_instruction}
"""


def run_chat_turn(db: Session, session_id: str, patient_id: int, user_message: str) -> str:
    language = detect_language(user_message)
    session_store.update(session_id, {"language": language})

    history = session_store.get_history_for_llm(session_id)
    messages = [{"role": "system", "content": build_system_prompt(language)}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    for _ in range(MAX_TOOL_ITERATIONS):
        assistant_message = get_chat_completion(messages, tools=TOOLS)

        tool_calls = getattr(assistant_message, "tool_calls", None)
        if not tool_calls:
            final_reply = (assistant_message.content or "").strip()
            if not final_reply:
                final_reply = "Sorry, I couldn't come up with a response. Could you rephrase that?"
            session_store.add_message(session_id, "user", user_message)
            session_store.add_message(session_id, "assistant", final_reply)
            return final_reply

        # The assistant asked to call one or more tools - append its request,
        # execute each one against the real database, and feed results back.
        messages.append({
            "role": "assistant",
            "content": assistant_message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {"name": tc.function.name, "arguments": tc.function.arguments},
                }
                for tc in tool_calls
            ],
        })

        for tc in tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if not isinstance(args, dict):
                # Groq sometimes sends arguments as the literal string "null"
                # for zero-argument tool calls, which json.loads turns into
                # Python None - guard against that (and any other non-dict).
                args = {}
            if not isinstance(args, dict):
                # Groq sometimes sends the literal string "null" for
                # no-arg tool calls; json.loads("null") -> None, and
                # **None crashes. Anything that isn't a dict just means
                # "no arguments".
                args = {}

            result = execute_tool_call(tc.function.name, args, db, patient_id)

            if tc.function.name in ("search_doctors", "get_doctor_availability", "get_doctor_reviews") \
                    and result.get("found") and result.get("doctors"):
                # Remember the most recently discussed doctor for coreference
                first_doctor = result["doctors"][0]
                session_store.update(session_id, {"current_doctor": first_doctor})
            elif tc.function.name in ("get_doctor_availability", "get_doctor_reviews") and result.get("doctor_name"):
                session_store.update(session_id, {"current_doctor": {"name": result["doctor_name"]}})

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": json.dumps(result, default=str),
            })

    # Safety net if the model loops without ever giving a final answer
    fallback = "I'm having trouble finishing that request right now - could you try rephrasing it?"
    session_store.add_message(session_id, "user", user_message)
    session_store.add_message(session_id, "assistant", fallback)
    return fallback


def _derive_session_id(patient_id: int, session_id: Optional[str] = None) -> str:
    """
    The frontend doesn't always send an explicit session_id (e.g. the
    query-param endpoint below only sends patient_id). Fall back to a
    stable per-patient session so conversation memory still persists
    across requests instead of silently starting a fresh session every
    single message.
    """
    return session_id or f"patient_{patient_id}"


@router.post("", response_model=ChatResponse)
@router.post("/", response_model=ChatResponse)
def chat_query_params(query: str, patient_id: int, session_id: Optional[str] = None,
                       db: Session = Depends(get_db)):
    """
    Matches calls like: POST /api/chat/?query=...&patient_id=1
    This is what the current frontend is actually sending - plain query
    params, no request body, no explicit session_id.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not query or not query.strip():
        raise HTTPException(status_code=400, detail="query cannot be empty")

    sid = _derive_session_id(patient_id, session_id)
    reply = run_chat_turn(db, sid, patient_id, query.strip())
    return ChatResponse(response=reply, session_id=sid)


@router.post("/message", response_model=ChatResponse)
def chat_message(payload: ChatRequest, db: Session = Depends(get_db)):
    """
    JSON-body version of the same endpoint, for any client that sends
    {session_id, patient_id, message} instead of query params.
    """
    patient = db.query(Patient).filter(Patient.id == payload.patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail="Patient not found")

    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="message cannot be empty")

    sid = _derive_session_id(payload.patient_id, payload.session_id)
    reply = run_chat_turn(db, sid, payload.patient_id, payload.message.strip())
    return ChatResponse(response=reply, session_id=sid)


@router.post("/reset/{session_id}")
def reset_chat_session(session_id: str):
    session_store.reset(session_id)
    return {"message": "Session cleared."}