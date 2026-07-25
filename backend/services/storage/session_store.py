import json
import time
import logging
import uuid

logger = logging.getLogger(__name__)

SESSION_TTL = 3600


class SessionStore:
    async def _redis(self):
        from services.redis import get_redis
        return await get_redis()

    async def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        r = await self._redis()
        data = {"created_at": time.time(), "messages": []}
        await r.setex(f"session:{session_id}", SESSION_TTL, json.dumps(data))
        logger.info(f"Created session {session_id}")
        return session_id

    async def add_message(self, session_id: str, role: str, content: str):
        r = await self._redis()
        key = f"session:{session_id}"
        msg = json.dumps({"role": role, "content": content})

        pipe = r.pipeline()
        pipe.get(key)
        results = await pipe.execute()
        raw = results[0]

        if not raw:
            return

        data = json.loads(raw)
        data["messages"].append({"role": role, "content": content})
        await r.setex(key, SESSION_TTL, json.dumps(data))

    async def get_conversation_history(self, session_id: str) -> list[dict]:
        r = await self._redis()
        raw = await r.get(f"session:{session_id}")
        if not raw:
            return []
        return json.loads(raw).get("messages", [])

    async def session_exists(self, session_id: str) -> bool:
        r = await self._redis()
        return await r.exists(f"session:{session_id}")

    async def delete_session(self, session_id: str):
        r = await self._redis()
        await r.delete(f"session:{session_id}")
        logger.info(f"Deleted session {session_id}")


session_store = SessionStore()
