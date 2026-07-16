from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from datetime import datetime
import logging

from backend.database import get_db
from backend.models import Doctor, Review
from backend.llm_helpers import extract_entities, generate_response
from backend.availability import get_available_slots

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])

@router.post("/")
def chat(
    query: str = Query(..., description="User's question about finding a doctor"),
    db: Session = Depends(get_db)
):
    """
    Chat endpoint to find doctors based on user query.
    """
    logger.info(f"Received chat query: {query}")
    
    try:
        # Step 1: Extract entities
        entities = extract_entities(query)
        specialty = entities.get("specialty")
        preferred_date_str = entities.get("preferred_date")
        preferred_time = entities.get("preferred_time")
        min_rating = entities.get("min_rating") or 0.0
        min_experience = entities.get("min_experience") or 0
        exclude_doctor = entities.get("exclude_doctor")
        
        logger.info(f"Extracted: specialty={specialty}, min_rating={min_rating}, min_experience={min_experience}")
        
        # Step 2: Query doctors
        doc_query = db.query(Doctor)
        
        # Apply filters
        if specialty:
            # Case-insensitive partial match
            doc_query = doc_query.filter(Doctor.specialty.ilike(f"%{specialty}%"))
        
        if min_experience > 0:
            doc_query = doc_query.filter(Doctor.years_of_experience >= min_experience)
        
        # Exclude a specific doctor by name
        if exclude_doctor:
            doc_query = doc_query.filter(
                ~((Doctor.first_name + " " + Doctor.last_name).ilike(f"%{exclude_doctor}%"))
            )
        
        # Get all candidates
        doctors = doc_query.all()
        logger.info(f"Found {len(doctors)} candidate doctors after basic filters")
        
        if not doctors:
            return {"response": "I couldn't find any doctors matching your criteria. Would you like to adjust your search?"}
        
        # Step 3: Compute average ratings and filter by rating
        from sqlalchemy import func
        
        results = []
        for doc in doctors:
            # Calculate average rating
            avg_rating_result = db.query(func.avg(Review.rating)).filter(Review.doctor_id == doc.id).scalar()
            avg_rating = float(avg_rating_result) if avg_rating_result else 0.0
            
            # Filter by min rating if specified (with tolerance)
            if min_rating and avg_rating < (float(min_rating) - 0.1):
                continue
            
            results.append({
                "id": doc.id,
                "first_name": doc.first_name,
                "last_name": doc.last_name,
                "specialty": doc.specialty,
                "years_experience": doc.years_of_experience,
                "avg_rating": avg_rating,
                "bio": doc.bio,
            })
        
        if not results:
            return {"response": f"No doctors found with rating {min_rating}+. Try lowering your rating requirement."}
        
        # Sort by rating desc, then experience desc
        results.sort(key=lambda x: (x['avg_rating'], x['years_experience']), reverse=True)
        logger.info(f"Found {len(results)} doctors after rating filter")
        
        # Step 4: Check availability for each doctor (if date specified)
        preferred_date = None
        if preferred_date_str:
            try:
                preferred_date = datetime.strptime(preferred_date_str, "%Y-%m-%d")
                logger.info(f"Checking availability for date: {preferred_date}")
            except ValueError:
                try:
                    # Try parsing "this Friday", "next Monday", etc.
                    from datetime import timedelta
                    days_map = {
                        "monday": 0, "tuesday": 1, "wednesday": 2,
                        "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6
                    }
                    # Simple parsing - just use today if not specified
                    preferred_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    logger.warning(f"Could not parse date '{preferred_date_str}', using today: {preferred_date}")
                except:
                    preferred_date = None
        
        # Check availability for each doctor
        for doc in results:
            if preferred_date:
                try:
                    slots = get_available_slots(doc['id'], preferred_date, db)
                    doc['available_slots'] = slots
                except Exception as e:
                    logger.error(f"Error checking availability for doctor {doc['id']}: {e}")
                    doc['available_slots'] = []
            else:
                doc['available_slots'] = []
        
        # If date specified, prioritize doctors with availability
        if preferred_date:
            # Keep all results, but sort by availability (available first)
            results.sort(key=lambda x: (1 if x['available_slots'] else 0, x['avg_rating'], x['years_experience']), reverse=True)
        
        # Step 5: Generate response using LLM
        response_text = generate_response(
            results,
            preferred_date.strftime("%Y-%m-%d") if preferred_date else None,
            preferred_time,
            query,
            exclude_doctor
        )
        
        return {"response": response_text}
        
    except Exception as e:
        logger.error(f"Unexpected error in chat endpoint: {e}", exc_info=True)
        return {"response": "I'm having trouble processing your request. Please try rephrasing your question or be more specific about what you're looking for."}