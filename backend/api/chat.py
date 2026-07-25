import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
from services.redis import get_redis
from services.llm import llm_client
from services.embedding import embedder
from services.storage import vector_store, session_store
from services import guardrails
from models.report import TailoringReport
from schemas.chat import ChatRequest
from schemas.common import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    error = guardrails.validate_message(request.message)
    if error:
        return ErrorResponse(error=error)

    redis = await get_redis()
    session_key = f"chat:{user_id}:{request.resume_id}"
    rate_error = await guardrails.check_rate_limit(redis, session_key)
    if rate_error:
        return ErrorResponse(error=rate_error)

    result = await db.execute(
        select(TailoringReport).where(
            TailoringReport.id == request.report_id,
            TailoringReport.user_id == user_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        return ErrorResponse(error="Report not found")

    stored_data = await vector_store.get_by_resume(db, str(request.resume_id))
    if not stored_data or not stored_data.get("documents"):
        return ErrorResponse(error="Resume not found")

    all_text = " ".join(stored_data["documents"])
    jd_text = report.jd_text or ""
    github_context = json.dumps(report.github_analysis, indent=2) if report.github_analysis else ""

    history = await session_store.get_conversation_history(session_key)

    query_embedding = embedder.embed_documents([request.message])[0]
    rag_results = await vector_store.query_by_resume(db, str(request.resume_id), query_embedding, top_k=5)

    rag_docs = []
    if rag_results and rag_results.get("documents") and rag_results["documents"][0]:
        rag_docs = rag_results["documents"][0]

    context = "\n\n".join(rag_docs) if rag_docs else all_text

    system_parts = [
        "You are a career coach helping a candidate understand their resume "
        "in the context of a specific job application.",
        "\n## STRICT RULES - follow at all times:",
        "- ONLY answer questions about: the candidate's resume, the job description, skills, experience, qualifications, interview prep, and career advice.",
        "- NEVER write code, generate code snippets, or explain programming concepts.",
        "- NEVER answer general knowledge questions unrelated to the job application.",
        "- NEVER discuss politics, religion, personal opinions, or any topic outside career coaching.",
        "- NEVER include URLs or links in your response.",
        '- If a question is off-topic, respond with: "I can only help with resume and job application questions. Please ask about your resume, skills, or the target role."',
        "- Keep responses concise and actionable - no fluff.",
        "- Do not invent information. If something is not in the resume or JD, say so.",
        "- Do not use markdown code blocks or inline code formatting.",
    ]

    if jd_text:
        system_parts.append(f"\nTarget Job Description:\n{jd_text}")
    if github_context:
        system_parts.append(f"\nGitHub Portfolio Context:\n{github_context}")
    system_parts.append(f"\nRelevant resume context:\n{context}")
    system_parts.append(
        "\nAnswer ONLY questions about the resume, job description, and GitHub data above. "
        "Stay strictly within the career coaching domain. "
        "Be specific, cite evidence when possible, and be honest if something is not found."
    )

    async def generator():
        try:
            yield f"data: {json.dumps({'type': 'status', 'message': 'Thinking...'})}\n\n"

            messages = [{"role": "system", "content": "\n".join(system_parts)}]
            for msg in history:
                messages.append({"role": msg["role"], "content": msg["content"]})
            messages.append({"role": "user", "content": request.message})
            await session_store.add_message(session_key, "user", request.message)

            full_content = ""
            async for token in llm_client.stream_chat(messages):
                full_content += token
                sanitized = guardrails.sanitize_output(full_content)
                yield f"data: {json.dumps({'type': 'text', 'content': sanitized})}\n\n"

            final = guardrails.sanitize_output(full_content)
            await session_store.add_message(session_key, "assistant", final)
            yield f"data: {json.dumps({'type': 'final', 'result': {'summary': 'Complete'}})}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
