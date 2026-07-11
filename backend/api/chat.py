import os
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from fastapi.responses import StreamingResponse

from services.vector_store import vector_store
from services.session_store import session_store
from services.llm_service import llm_service
from services.embedding_service import embedder
from schemas.chat import ChatRequest
from schemas.common import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()


async def _get_user_id(authorization: str = Header(...)) -> UUID:
    import jwt
    token = authorization.replace("Bearer ", "")
    payload = jwt.decode(token, os.environ.get("JWT_SECRET", ""), algorithms=["HS256"])
    return UUID(payload["sub"])


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user_id: UUID = Depends(_get_user_id),
):
    stored_data = vector_store.get_by_resume(str(request.resume_id))

    if not stored_data or not stored_data.get("documents"):
        return ErrorResponse(error="Resume not found")

    all_text = " ".join(stored_data["documents"])

    # Get or create chat session
    session_key = f"chat:{user_id}:{request.resume_id}"
    session_id = await session_store.create_session()
    history = await session_store.get_conversation_history(session_key)

    query_embedding = embedder.embed_documents([request.message])[0]
    rag_results = vector_store.query_by_resume(str(request.resume_id), query_embedding, top_k=5)

    rag_docs = []
    if rag_results and rag_results.get("documents") and rag_results["documents"][0]:
        rag_docs = rag_results["documents"][0]

    context = "\n\n".join(rag_docs) if rag_docs else all_text

    # Use shared LLM key
    api_key = os.environ.get("LLM_API_KEY", "")
    base_url = "https://api.openai.com/v1"
    model = "gpt-4o-mini"

    async def generator():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Thinking...'})}\n\n"

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a career coach helping a candidate understand their resume "
                        "in the context of a job application. "
                        "Answer questions based on the resume context provided below. "
                        "Be specific, cite evidence from the resume when possible, "
                        "and be honest if something is not found.\n\n"
                        f"Relevant resume context:\n{context}\n"
                    ),
                }
            ]

            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})

            messages.append({"role": "user", "content": request.message})
            await session_store.add_message(session_key, "user", request.message)

            full_content = ""
            async for token in llm_service._stream_chat(messages, api_key, base_url, model):
                full_content += token
                yield f"data: {json.dumps({'type': 'text', 'content': token})}\n\n"

            await session_store.add_message(session_key, "assistant", full_content)
            yield f"data: {json.dumps({'type': 'final', 'result': {'summary': 'Complete'}})}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
