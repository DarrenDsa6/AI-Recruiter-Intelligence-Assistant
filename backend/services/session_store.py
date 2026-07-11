import uuid
import json
import time
import logging

logger = logging.getLogger(__name__)


class SessionStore:
    def __init__(self):
        self.ttl = 3600

    async def _redis(self):
        from services.redis_client import get_redis
        return await get_redis()

    async def create_session(self):
        session_id = str(uuid.uuid4())
        r = await self._redis()
        data = {
            "created_at": time.time(),
            "messages": []
        }
        await r.setex(f"session:{session_id}", self.ttl, json.dumps(data))
        logger.info(f"Created session {session_id}")
        return session_id

    async def add_message(self, session_id, role, content):
        r = await self._redis()
        key = f"session:{session_id}"
        raw = await r.get(key)
        if not raw:
            return
        data = json.loads(raw)
        data["messages"].append({"role": role, "content": content})
        await r.setex(key, self.ttl, json.dumps(data))

    async def get_conversation_history(self, session_id):
        r = await self._redis()
        raw = await r.get(f"session:{session_id}")
        if not raw:
            return []
        return json.loads(raw).get("messages", [])

    async def session_exists(self, session_id):
        r = await self._redis()
        return await r.exists(f"session:{session_id}")

    async def delete_session(self, session_id):
        r = await self._redis()
        await r.delete(f"session:{session_id}")
        logger.info(f"Deleted session {session_id}")


session_store = SessionStore()
