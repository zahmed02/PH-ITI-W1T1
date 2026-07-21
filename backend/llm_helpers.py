# backend/llm_helpers.py
import os
import logging
import re
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
                         temperature: float = 0.2, max_tokens: int = 700):
    """
    Thin wrapper around the Groq chat completion call so callers don't
    touch the client directly. Returns the raw message object from the
    API (has .content, .tool_calls, etc).
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

    response = client.chat.completions.create(**kwargs)
    return response.choices[0].message
