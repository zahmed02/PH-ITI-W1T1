from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import json
import logging

from backend.database import get_db
from backend.models import Doctor, Review, Patient
from backend.llm_helpers import client, generate_response, detect_language
from backend.availability import get_available_slots, get_weekly_availability
from backend.booking import book_appointment
from backend.session_store import session_store

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["Chat"])

def understand_query(query: str, history: list) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    history_text = ""
    if history:
        history_text = "Previous conversation:\n" + "\n".join([
            f"{'User' if h['role']=='user' else 'Assistant'}: {h['content']}"
            for h in history[-8:]
        ])

    prompt = f"""
Today is {today}.
{history_text}

User query: "{query}"

Interpret the user's request. Return ONLY a valid JSON object with these keys:
- "action": one of ["search", "availability", "book", "symptom", "list_all"]
- "doctor_name": the full name of the doctor mentioned in the CURRENT query, or null if none.
- "specialty": the medical specialty mentioned or inferred, or null.
- "date": the date in YYYY-MM-DD format if mentioned, else null.
- "time": the time in HH:MM 24-hour format if mentioned, else null.
- "min_rating": a number if rating is mentioned, else null.
- "min_experience": a number if experience is mentioned, else null.

Important:
- If the user mentions a doctor's name in the query, capture it exactly.
- If the user uses pronouns like "us ka", "wo", "un ka", or "unhon ne", refer to the last mentioned doctor from the history.
- If the query is about a doctor that was mentioned in the history but not in the current query, use the context to infer.

For symptoms, infer the specialty (e.g., "headache" -> "Neurology", "chest pain" -> "Cardiology").
Return ONLY the JSON object.
"""
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=400
        )
        raw = resp.choices[0].message.content.strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        data = json.loads(raw)
        logger.info(f"LLM understanding: {data}")
        return data
    except Exception as e:
        logger.error(f"LLM understanding failed: {e}")
        return {
            "action": "search",
            "doctor_name": None,
            "specialty": None,
            "date": None,
            "time": None,
            "min_rating": None,
            "min_experience": None
        }

def get_doctor_from_name(db: Session, name: str):
    if not name:
        return None
    # Try full name match
    doctor = db.query(Doctor).filter(
        func.concat(Doctor.first_name, ' ', Doctor.last_name).ilike(f"%{name}%")
    ).first()
    if doctor:
        return doctor
    # Try partial match on first or last name
    parts = name.split()
    if len(parts) == 1:
        doctor = db.query(Doctor).filter(
            (func.lower(Doctor.first_name).like(f"%{name.lower()}%")) |
            (func.lower(Doctor.last_name).like(f"%{name.lower()}%"))
        ).first()
    else:
        first, last = parts[0], parts[-1]
        doctor = db.query(Doctor).filter(
            func.lower(Doctor.first_name).like(f"%{first.lower()}%"),
            func.lower(Doctor.last_name).like(f"%{last.lower()}%")
        ).first()
    return doctor

@router.post("/")
def chat(
    query: str = Query(..., description="User's question"),
    patient_id: int = Query(None, description="Patient ID"),
    session_id: str = Query(None, description="Session ID"),
    db: Session = Depends(get_db)
):
    logger.info(f"Chat: {query} | patient_id: {patient_id} | session_id: {session_id}")

    if not session_id:
        if patient_id:
            session_id = f"patient_{patient_id}"
        else:
            session_id = f"guest_{datetime.now().timestamp()}"
    session = session_store.get(session_id)
    language = detect_language(query)
    session["language"] = language
    session_store.add_message(session_id, "user", query)

    # 1. Understand the query with LLM
    understanding = understand_query(query, session.get("history", []))
    action = understanding.get("action", "search")
    doctor_name = understanding.get("doctor_name")
    specialty = understanding.get("specialty")
    date_str = understanding.get("date")
    time_str = understanding.get("time")
    min_rating = understanding.get("min_rating") or 0.0
    min_experience = understanding.get("min_experience") or 0

    logger.info(f"Parsed: action={action}, doctor_name={doctor_name}, specialty={specialty}, date={date_str}, time={time_str}")

    # Store parameters in session for context
    if doctor_name:
        session["last_doctor_name"] = doctor_name
    if date_str:
        session["last_date"] = date_str
    if time_str:
        session["last_time"] = time_str
    session_store.update(session_id, session)

    # Resolve doctor: ONLY use the doctor from the CURRENT query
    # Do NOT fall back to session's last doctor unless the query explicitly refers to it
    doctor = None
    if doctor_name:
        doctor = get_doctor_from_name(db, doctor_name)
        if doctor:
            session["last_doctor_id"] = doctor.id
            session["last_doctor_name"] = f"{doctor.first_name} {doctor.last_name}"
            session_store.update(session_id, session)
    else:
        # Only if the query doesn't mention a doctor, check if it's a follow-up
        # about the last doctor (e.g., "un ka schedule batao")
        lower_query = query.lower()
        if any(word in lower_query for word in ['un', 'us', 'wo', 'unhon', 'unho', 'he', 'she', 'they']):
            if session.get("last_doctor_id"):
                doctor = db.query(Doctor).filter(Doctor.id == session["last_doctor_id"]).first()
                if doctor:
                    # Update the context to confirm we're talking about this doctor
                    session["last_doctor_name"] = f"{doctor.first_name} {doctor.last_name}"
                    session_store.update(session_id, session)

    # If we have a doctor from the current query, use it
    if not doctor and doctor_name:
        # Try to find the doctor even if it's not a perfect match
        possible = db.query(Doctor).filter(
            (func.lower(Doctor.first_name).like(f"%{doctor_name.lower()}%")) |
            (func.lower(Doctor.last_name).like(f"%{doctor_name.lower()}%"))
        ).first()
        if possible:
            doctor = possible
            session["last_doctor_id"] = doctor.id
            session["last_doctor_name"] = f"{doctor.first_name} {doctor.last_name}"
            session_store.update(session_id, session)

    # 2. Execute action
    raw_result = {}

    if action == "book":
        if not patient_id:
            raw_result = {"error": "Patient ID missing", "message": "I need your patient ID to book."}
        else:
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                raw_result = {"error": "Patient not found", "message": f"Patient with ID {patient_id} not found."}
            elif not doctor:
                raw_result = {"error": "Doctor missing", "message": "Please tell me which doctor you want to book with."}
            elif not date_str:
                raw_result = {"error": "Date missing", "message": f"Please provide a date for the appointment."}
            elif not time_str:
                raw_result = {"error": "Time missing", "message": f"Please provide a time for the appointment."}
            else:
                booking_result = book_appointment(
                    db=db,
                    doctor_name=f"{doctor.first_name} {doctor.last_name}",
                    patient_id=patient_id,
                    date_expr=date_str,
                    time_expr=time_str
                )
                raw_result = booking_result

    elif action == "availability":
        if not doctor:
            raw_result = {"error": "Doctor missing", "message": "Please tell me which doctor's schedule you want to see."}
        else:
            date_to_check = date_str or session.get("last_date")
            if date_to_check:
                slots = get_available_slots(doctor.id, date_to_check, db)
                raw_result = {
                    "doctor": f"Dr. {doctor.first_name} {doctor.last_name}",
                    "specialty": doctor.specialty,
                    "date": date_to_check,
                    "available_slots": slots if slots else []
                }
            else:
                weekly = get_weekly_availability(doctor.id, db)
                raw_result = {
                    "doctor": f"Dr. {doctor.first_name} {doctor.last_name}",
                    "specialty": doctor.specialty,
                    "weekly_schedule": weekly
                }

    elif action == "symptom":
        if not specialty:
            specialty = "General Medicine"
        doctors = db.query(Doctor).filter(Doctor.specialty.ilike(f"%{specialty}%")).all()
        if not doctors:
            raw_result = {"error": "No doctors found", "message": f"No doctors found for specialty '{specialty}'."}
        else:
            results = []
            for doc in doctors:
                avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doc.id).scalar() or 0.0
                results.append({
                    "id": doc.id,
                    "name": f"Dr. {doc.first_name} {doc.last_name}",
                    "specialty": doc.specialty,
                    "experience": doc.years_of_experience,
                    "rating": float(avg_rating)
                })
            results.sort(key=lambda x: x['rating'], reverse=True)
            if results:
                session["last_doctor_name"] = results[0]["name"]
            raw_result = {"specialty": specialty, "doctors": results[:5]}

    elif action == "list_all":
        date_to_check = date_str or session.get("last_date")
        if date_to_check:
            try:
                date_obj = datetime.strptime(date_to_check, "%Y-%m-%d").date()
            except:
                date_obj = datetime.now().date()
        else:
            date_obj = datetime.now().date()
        all_doctors = db.query(Doctor).all()
        results = []
        for doc in all_doctors:
            avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doc.id).scalar() or 0.0
            slots = get_available_slots(doc.id, date_obj.strftime("%Y-%m-%d"), db)
            results.append({
                "name": f"Dr. {doc.first_name} {doc.last_name}",
                "specialty": doc.specialty,
                "experience": doc.years_of_experience,
                "rating": float(avg_rating),
                "available_slots": slots if slots else []
            })
        results.sort(key=lambda x: x['rating'], reverse=True)
        raw_result = {"date": date_obj.strftime("%Y-%m-%d"), "doctors": results[:5]}

    else:  # search
        q = db.query(Doctor)
        if specialty:
            q = q.filter(Doctor.specialty.ilike(f"%{specialty}%"))
        if min_experience > 0:
            q = q.filter(Doctor.years_of_experience >= min_experience)
        if doctor_name:
            q = q.filter(
                func.concat(Doctor.first_name, ' ', Doctor.last_name).ilike(f"%{doctor_name}%")
            )
        doctors = q.all()
        if not doctors:
            raw_result = {"error": "No doctors found", "message": "No doctors matched your criteria."}
        else:
            results = []
            for doc in doctors:
                avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doc.id).scalar() or 0.0
                if min_rating and avg_rating < (float(min_rating) - 0.1):
                    continue
                results.append({
                    "id": doc.id,
                    "name": f"Dr. {doc.first_name} {doc.last_name}",
                    "specialty": doc.specialty,
                    "experience": doc.years_of_experience,
                    "rating": float(avg_rating)
                })
            if not results:
                raw_result = {"error": "No doctors found", "message": f"No doctors with rating {min_rating}+."}
            else:
                results.sort(key=lambda x: (x['rating'], x['experience']), reverse=True)
                if results:
                    session["last_doctor_name"] = results[0]["name"]
                raw_result = {"doctors": results[:5]}

    # 3. Generate final response using LLM
    final_response = generate_response(
        user_query=query,
        action_result=raw_result,
        history=session.get("history", []),
        language=language
    )
    session_store.add_message(session_id, "assistant", final_response)
    return {"response": final_response}