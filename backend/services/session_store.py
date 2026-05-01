import uuid
import time


class SessionStore:
    def __init__(self):
        self.sessions = {}
        self.ttl = 3600  # 1 hour

    def create_session(self):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": time.time()
        }
        return session_id

    def get_expired_sessions(self):
        now = time.time()

        expired = []

        for session_id, data in self.sessions.items():
            if now - data["created_at"] > self.ttl:
                expired.append(session_id)

        return expired

    def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]

session_store = SessionStore()