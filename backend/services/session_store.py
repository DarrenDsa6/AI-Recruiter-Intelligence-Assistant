import uuid
import time
import logging

logger = logging.getLogger(__name__)


class SessionStore:
    def __init__(self):
        self.sessions = {}
        self.ttl = 3600

    def create_session(self):
        session_id = str(uuid.uuid4())
        self.sessions[session_id] = {
            "created_at": time.time(),
            "messages": []
        }
        logger.info(f"Created session {session_id}")
        return session_id

    def add_message(self, session_id, role, content):
        if session_id in self.sessions:
            self.sessions[session_id]["messages"].append({
                "role": role,
                "content": content
            })

    def get_conversation_history(self, session_id):
        if session_id in self.sessions:
            return self.sessions[session_id]["messages"]
        return []

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
            logger.info(f"Deleted session {session_id}")


session_store = SessionStore()
