from collections import defaultdict
from datetime import datetime

class SessionStore:
    def __init__(self):
        self.sessions = defaultdict(lambda: {
            "history": [],
            "last_doctor_id": None,
            "last_doctor_name": None,
            "last_date": None,
            "last_time": None,
            "language": "en"
        })

    def get(self, session_id: str):
        return self.sessions[session_id]

    def update(self, session_id: str, data: dict):
        self.sessions[session_id].update(data)

    def add_message(self, session_id: str, role: str, content: str):
        self.sessions[session_id]["history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        if len(self.sessions[session_id]["history"]) > 10:
            self.sessions[session_id]["history"] = self.sessions[session_id]["history"][-10:]

session_store = SessionStore()