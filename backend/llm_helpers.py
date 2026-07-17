import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def extract_entities(query: str) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    prompt = f"""
Extract the following information from the user's query about finding or booking a doctor.

Today's date is {today}.
User query: "{query}"

Return ONLY a valid JSON object with these exact keys:
- "intent": either "search" or "book".
- "specialty": medical specialty, or null if none.
- "preferred_date": the date mentioned (e.g., "tomorrow", "this Friday", or YYYY-MM-DD), or null if none.
- "preferred_time": time preference (morning, afternoon, evening, or specific hour like 10am), or null if none.
- "min_rating": minimum rating (1-5), or null if none.
- "min_experience": minimum years of experience, or null if none.
- "exclude_doctor": specific doctor name to exclude, or null if none.
- "doctor_name": if the user explicitly names a doctor, put the full name WITHOUT any title (e.g., "James Wilson", not "Dr. James Wilson").

Interpretations:
- "good ratings" → min_rating: 4.0
- "highly rated" → min_rating: 4.5
- "experienced" → min_experience: 10
- "book", "schedule", "make an appointment" → intent: "book"

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
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        entities = json.loads(raw)

        defaults = {
            "intent": "search",
            "specialty": None,
            "preferred_date": None,
            "preferred_time": None,
            "min_rating": None,
            "min_experience": None,
            "exclude_doctor": None,
            "doctor_name": None
        }
        for key, default in defaults.items():
            if key not in entities or entities[key] is None:
                entities[key] = default
            elif isinstance(entities[key], str) and entities[key].lower() == "null":
                entities[key] = default

        logger.info(f"Extracted entities: {entities}")
        return entities
    except Exception as e:
        logger.error(f"Error extracting entities: {e}")
        return {
            "intent": "search",
            "specialty": None,
            "preferred_date": None,
            "preferred_time": None,
            "min_rating": None,
            "min_experience": None,
            "exclude_doctor": None,
            "doctor_name": None
        }

def generate_response(doctors, preferred_date, preferred_time, user_query, exclude_doctor=None, booking_result=None):
    """
    Generate a natural language response from a list of doctors and availability.
    If booking_result is provided, generate a booking confirmation/error response.
    """
    # --- Booking response ---
    if booking_result:
        if booking_result.get("success"):
            prompt = f"""
The user said: "{user_query}"
You have successfully booked an appointment with Dr. {booking_result.get('doctor_name')} on {booking_result.get('date')} at {booking_result.get('time')}.
Appointment ID: {booking_result.get('appointment_id')}

Generate a friendly confirmation message for the user.
"""
        else:
            prompt = f"""
The user said: "{user_query}"
Booking failed because: {booking_result.get('message')}

Generate a helpful response explaining why and suggest alternatives (e.g., other times or doctors).
"""
        try:
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=200
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error generating booking response: {e}")
            return booking_result.get("message", "Booking could not be completed.")

    # --- Search response ---
    if not doctors:
        return "I couldn't find any doctors matching your criteria. Would you like to adjust your preferences?"
    
    # Format doctor info
    doctor_list = []
    for doc in doctors:
        doc_str = f"Dr. {doc['first_name']} {doc['last_name']} ({doc['specialty']}), {doc['years_experience']} years exp, rating {doc['avg_rating']:.1f}"
        if 'available_slots' in doc and doc['available_slots']:
            slots = ', '.join(doc['available_slots'][:3])
            doc_str += f", available: {slots}"
        elif preferred_date and 'available_slots' in doc and not doc['available_slots']:
            doc_str += f", no available slots on {preferred_date}"
        doctor_list.append(doc_str)
    
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
        return f"I found {len(doctors)} doctor(s) matching your criteria. Please visit /doctors to see the full list, or refine your search."