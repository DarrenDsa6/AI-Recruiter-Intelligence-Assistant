from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import logging

from services.vector_store import vector_store
from services.session_store import session_store
from services.llm_service import llm_service
from services.embedding_service import embedder

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatRequest(BaseModel):
    session_id: str
    message: str


@router.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    stored_data = vector_store.get_by_session(request.session_id)

    if not stored_data or not stored_data.get("documents"):
        return {"error": "Session not found"}

    all_documents = stored_data["documents"]
    all_text = " ".join(all_documents)
    history = session_store.get_conversation_history(request.session_id)

    query_embedding = embedder.embed_documents([request.message])[0]
    rag_results = vector_store.query_by_session(
        request.session_id, query_embedding, top_k=5
    )

    rag_docs = []
    if rag_results and rag_results.get("documents") and rag_results["documents"][0]:
        rag_docs = rag_results["documents"][0]

    context = "\n\n".join(rag_docs) if rag_docs else all_text

    def generator():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Thinking...'})}\n\n"

            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a recruiter AI assistant analyzing a candidate's resume. "
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

            session_store.add_message(request.session_id, "user", request.message)

            full_content = ""
            for token in llm_service._stream_chat(messages):
                full_content += token
                yield f"data: {json.dumps({'type': 'text', 'content': token})}\n\n"

            session_store.add_message(request.session_id, "assistant", full_content)

            yield f"data: {json.dumps({'type': 'final', 'result': {'summary': 'Complete'}})}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
