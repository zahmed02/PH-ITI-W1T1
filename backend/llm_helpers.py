import os
import logging
import re
import time
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
client = Groq(api_key=os.getenv("GROQ_API_KEY"))

CHAT_MODEL = "llama-3.1-8b-instant"


def detect_language(text: str) -> str:
    urdu_chars = re.compile(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF\uFB50-\uFDFF\uFE70-\uFEFF]')
    return "ur" if urdu_chars.search(text) else "en"


def get_chat_completion(messages: list, tools: list = None, tool_choice: str = "auto",
                         temperature: float = 0.2, max_tokens: int = 700, max_attempts: int = 3):
    """
    Thin wrapper around the Groq chat completion call so callers don't
    touch the client directly. Returns the raw message object from the
    API (has .content, .tool_calls, etc).

    Retries on transient failures (rate limits, timeouts, brief network
    blips) with a short backoff, since a single dropped request previously
    surfaced all the way to the user as an unhandled 500 / "Sorry, an
    error occurred" even though a retry a second later would succeed.
    """
    kwargs = {
        "model": CHAT_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        kwargs["tools"] = tools
        kwargs["tool_choice"] = tool_choice

    last_error = None
    for attempt in range(1, max_attempts + 1):
        try:
            response = client.chat.completions.create(**kwargs)
            return response.choices[0].message
        except Exception as e:
            last_error = e
            logger.warning(f"Groq chat completion attempt {attempt}/{max_attempts} failed: {e}")
            if attempt < max_attempts:
                time.sleep(0.5 * attempt)

    raise last_error