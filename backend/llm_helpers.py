import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_entities(query: str) -> dict:
    """
    Extract structured information from user query using LLM.
    Returns a dict with keys: specialty, preferred_date, preferred_time, min_rating, min_experience
    """
    prompt = f"""
Extract the following information from the user's query about finding a doctor.

User query: "{query}"

Return ONLY a valid JSON object with these exact keys:
- "specialty": the medical specialty mentioned (e.g., cardiology, neurology, pediatrics, orthopedics), or null if none
- "preferred_date": the date mentioned in YYYY-MM-DD format, or null if none
- "preferred_time": the time preference (morning, afternoon, evening, or specific hour like 10am), or null if none
- "min_rating": the minimum rating mentioned (as a number 1-5), or null if none
- "min_experience": the minimum years of experience mentioned (as a number), or null if none
- "exclude_doctor": specific doctor name to exclude, or null if none

If a user says "good ratings", interpret that as min_rating: 4.0.
If a user says "highly rated", interpret that as min_rating: 4.5.
If a user says "experienced", interpret that as min_experience: 10.

Do not add any extra text. Only return valid JSON.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300
        )
        raw = response.choices[0].message.content.strip()
        
        # Extract JSON from the response (handle potential markdown)
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        
        entities = json.loads(raw)
        
        # Ensure all keys exist with defaults
        defaults = {
            "specialty": None,
            "preferred_date": None,
            "preferred_time": None,
            "min_rating": None,
            "min_experience": None,
            "exclude_doctor": None
        }
        for key, default in defaults.items():
            if key not in entities or entities[key] is None:
                entities[key] = default
            # If it's a string "null", convert to None
            elif isinstance(entities[key], str) and entities[key].lower() == "null":
                entities[key] = default
        
        logger.info(f"Extracted entities: {entities}")
        return entities
    except Exception as e:
        logger.error(f"Error extracting entities: {e}")
        # Return default values
        return {
            "specialty": None,
            "preferred_date": None,
            "preferred_time": None,
            "min_rating": None,
            "min_experience": None,
            "exclude_doctor": None
        }

def generate_response(doctors, preferred_date, preferred_time, user_query, exclude_doctor=None):
    """
    Generate a natural language response from a list of doctors and availability.
    """
    if not doctors:
        return "I couldn't find any doctors matching your criteria. Would you like to adjust your preferences?"
    
    # Format doctor info
    doctor_list = []
    for doc in doctors:
        doc_str = f"Dr. {doc['first_name']} {doc['last_name']} ({doc['specialty']}), {doc['years_experience']} years exp, rating {doc['avg_rating']:.1f}"
        
        # Add availability if checked
        if 'available_slots' in doc and doc['available_slots']:
            slots = ', '.join(doc['available_slots'][:3])  # Show top 3 slots
            doc_str += f", available: {slots}"
        elif preferred_date and 'available_slots' in doc and not doc['available_slots']:
            doc_str += f", no available slots on {preferred_date}"
        doctor_list.append(doc_str)
    
    # Check if there are any matching doctors that are available
    available_doctors = [d for d in doctors if d.get('available_slots')]
    has_availability = bool(available_doctors)
    
    prompt = f"""
User asked: "{user_query}"
Preferred date: {preferred_date or "not specified"}
Preferred time: {preferred_time or "not specified"}
{('Exclude doctor: ' + exclude_doctor) if exclude_doctor else ''}

Here are the matching doctors:
{chr(10).join(doctor_list)}

{'Availability checked: Yes' if preferred_date else 'Availability checked: No'}

Based on this information, generate a helpful, concise response for the user.
- If a preferred date/time was specified and doctors are available, recommend the best one (highest rating, most experience).
- If the best doctor is not available, suggest alternatives.
- If no doctors are available on the preferred date, suggest a later date or ask if they want to wait.
- If there are no matching doctors at all, suggest adjusting criteria.

Be friendly and professional. Keep it under 150 words.
"""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error generating response: {e}")
        # Fallback response
        return f"I found {len(doctors)} doctor(s) matching your criteria. Please visit /doctors to see the full list, or refine your search."