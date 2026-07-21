# backend/llm_helpers.py
import os
import json
import logging
from groq import Groq
from dotenv import load_dotenv
import re

load_dotenv()
logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def detect_language(text: str) -> str:
    urdu_chars = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    return "ur" if urdu_chars.search(text) else "en"

def generate_response(user_query: str, action_result: dict, history: list, language: str = "en") -> str:
    """Generate a natural language response using the LLM, based on the action result."""
    history_text = ""
    if history:
        history_text = "Previous conversation:\n" + "\n".join([
            f"{'User' if h['role']=='user' else 'Assistant'}: {h['content']}"
            for h in history[-6:]
        ])

    result_text = json.dumps(action_result, indent=2, default=str)

    prompt = f"""
{history_text}

User asked: "{user_query}"

Action result (JSON):
{result_text}

Now, generate a friendly, helpful, and natural response for the user based on the action result.
- If it's a list of doctors, summarize them concisely.
- If it's a booking confirmation, confirm it.
- If it's an error, explain it clearly and suggest alternatives.
- If it's a schedule, list the available times.
- Never mention JSON or technical details.
- Use the language that matches the user's query (the user wrote in {'Urdu' if language=='ur' else 'English'}).

Keep it under 250 words.
"""
    try:
        resp = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
            max_tokens=300
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Response generation failed: {e}")
        return "I'm having trouble generating a response. Please try again."