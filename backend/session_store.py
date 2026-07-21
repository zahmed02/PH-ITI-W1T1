from collections import defaultdict
from datetime import datetime
from threading import Lock

MAX_HISTORY_MESSAGES = 20  # keep last 10 user/assistant turns


class SessionStore:
    """
    In-memory per-session conversation state.

    NOTE: This is process-local memory - it resets if the server restarts
    and won't be shared across multiple worker processes. That's fine for
    a single-process dev/demo deployment, but if you deploy with multiple
    Uvicorn/Gunicorn workers you'll need to move this to Redis or the
    database instead, or sessions will randomly appear to "forget"
    depending on which worker handles a given request.
    """

    def __init__(self):
        self.sessions = defaultdict(lambda: {
            "history": [],          # list of {"role": ..., "content": ...} - what gets sent to the LLM
            "current_doctor": None,  # last doctor discussed, for lightweight continuity
            "language": "en",
        })
        self._lock = Lock()

    def get(self, session_id: str) -> dict:
        with self._lock:
            return self.sessions[session_id]

    def update(self, session_id: str, data: dict):
        with self._lock:
            self.sessions[session_id].update(data)

    def add_message(self, session_id: str, role: str, content: str):
        with self._lock:
            session = self.sessions[session_id]
            session["history"].append({"role": role, "content": content})
            if len(session["history"]) > MAX_HISTORY_MESSAGES:
                session["history"] = session["history"][-MAX_HISTORY_MESSAGES:]

    def get_history_for_llm(self, session_id: str) -> list:
        """Returns a clean list of {role, content} dicts ready to feed to the LLM."""
        with self._lock:
            return list(self.sessions[session_id]["history"])

    def reset(self, session_id: str):
        with self._lock:
            if session_id in self.sessions:
                del self.sessions[session_id]


session_store = SessionStore()
