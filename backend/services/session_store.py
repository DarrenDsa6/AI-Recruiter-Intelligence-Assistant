import uuid
import time
import heapq
import logging

logger = logging.getLogger(__name__)


class SessionStore:
    def __init__(self):
        self.sessions = {}
        self.ttl = 3600
        self._expiry_heap = []

    def create_session(self):
        session_id = str(uuid.uuid4())
        expiry = time.time() + self.ttl
        self.sessions[session_id] = {
            "created_at": time.time(),
            "expires_at": expiry,
            "messages": []
        }
        heapq.heappush(self._expiry_heap, (expiry, session_id))
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
        while self._expiry_heap and self._expiry_heap[0][0] <= now:
            expiry, session_id = heapq.heappop(self._expiry_heap)
            if session_id in self.sessions:
                expired.append(session_id)
        return expired

    def delete_session(self, session_id):
        if session_id in self.sessions:
            del self.sessions[session_id]
            logger.info(f"Deleted session {session_id}")


session_store = SessionStore()
