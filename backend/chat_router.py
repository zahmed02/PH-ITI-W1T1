from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from backend.database import get_db
from backend.models import Doctor, Review, Patient
from backend.llm_helpers import extract_entities, generate_response
from backend.availability import get_available_slots
from backend.date_parser import parse_date_expression, parse_time_expression
from backend.booking import book_appointment

logger = logging.getLogger(__name__)

# Changed prefix from "/api/chat" to "/chat" will be mounted under /api in main.py
router = APIRouter(prefix="/chat", tags=["Chat"])

@router.post("/")
def chat(
    query: str = Query(..., description="User's question about finding or booking a doctor"),
    patient_id: int = Query(None, description="Required for booking; the ID of the patient making the appointment"),
    db: Session = Depends(get_db)
):
    logger.info(f"Received chat query: {query} | patient_id: {patient_id}")
    try:
        # Step 1: Extract entities
        entities = extract_entities(query)
        intent = entities.get("intent", "search")
        specialty = entities.get("specialty")
        preferred_date_str = entities.get("preferred_date")
        preferred_time_str = entities.get("preferred_time")
        min_rating = entities.get("min_rating") or 0.0
        min_experience = entities.get("min_experience") or 0
        exclude_doctor = entities.get("exclude_doctor")
        doctor_name = entities.get("doctor_name")

        # Log extracted entities
        logger.info(f"Extracted entities: {entities}")
        logger.info(f"Intent: {intent}, doctor_name: {doctor_name}")

        # Step 2: Handle booking intent
        if intent == "book":
            if not patient_id:
                return {"response": "I need to know who you are. Please provide your patient ID."}
            patient = db.query(Patient).filter(Patient.id == patient_id).first()
            if not patient:
                return {"response": f"Patient with ID {patient_id} not found. Please register first."}

            if not doctor_name:
                return {"response": "I need the doctor's name. Please specify which doctor you want to book with."}

            booking_result = book_appointment(
                db=db,
                doctor_name=doctor_name,
                patient_id=patient_id,
                date_expr=preferred_date_str,
                time_expr=preferred_time_str
            )
            response_text = generate_response(
                doctors=[],
                preferred_date=preferred_date_str,
                preferred_time=preferred_time_str,
                user_query=query,
                exclude_doctor=None,
                booking_result=booking_result
            )
            return {"response": response_text}

        # Step 3: Search flow
        preferred_date = None
        if preferred_date_str:
            preferred_date = parse_date_expression(preferred_date_str)
            if preferred_date is None:
                logger.warning(f"Could not parse date: '{preferred_date_str}'")

        preferred_time_range = None
        if preferred_time_str:
            preferred_time_range = parse_time_expression(preferred_time_str)
            if preferred_time_range is None:
                logger.warning(f"Could not parse time: '{preferred_time_str}'")

        doc_query = db.query(Doctor)
        if specialty:
            doc_query = doc_query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
        if min_experience > 0:
            doc_query = doc_query.filter(Doctor.years_of_experience >= min_experience)
        if exclude_doctor:
            doc_query = doc_query.filter(
                ~((Doctor.first_name + " " + Doctor.last_name).ilike(f"%{exclude_doctor}%"))
            )

        doctors = doc_query.all()
        if not doctors:
            return {"response": "I couldn't find any doctors matching your criteria. Would you like to adjust your search?"}

        from sqlalchemy import func
        results = []
        for doc in doctors:
            avg_rating = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doc.id).scalar() or 0.0
            if min_rating and avg_rating < (float(min_rating) - 0.1):
                continue
            results.append({
                "id": doc.id,
                "first_name": doc.first_name,
                "last_name": doc.last_name,
                "specialty": doc.specialty,
                "years_experience": doc.years_of_experience,
                "avg_rating": float(avg_rating),
                "bio": doc.bio,
            })

        if not results:
            return {"response": f"No doctors found with rating {min_rating}+. Try lowering your rating requirement."}

        results.sort(key=lambda x: (x['avg_rating'], x['years_experience']), reverse=True)

        if preferred_date:
            for doc in results:
                try:
                    slots = get_available_slots(
                        doc['id'],
                        preferred_date,
                        db,
                        preferred_time_range=preferred_time_range
                    )
                    doc['available_slots'] = slots
                except Exception as e:
                    logger.error(f"Availability check failed for doctor {doc['id']}: {e}")
                    doc['available_slots'] = []
        else:
            for doc in results:
                doc['available_slots'] = []

        if preferred_date:
            results.sort(key=lambda x: (1 if x['available_slots'] else 0, x['avg_rating'], x['years_experience']), reverse=True)

        response_text = generate_response(
            results,
            preferred_date.strftime("%Y-%m-%d") if preferred_date else None,
            preferred_time_str,
            query,
            exclude_doctor
        )

        return {"response": response_text}

    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return {"response": "I'm having trouble processing your request. Please try rephrasing your question or be more specific about what you're looking for."}