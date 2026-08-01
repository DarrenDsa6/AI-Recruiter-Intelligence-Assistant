import asyncio
import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
from services.redis import get_redis
from services.llm import llm_client
from services.llm.prompts import CHAT_SYSTEM_PROMPT_TEMPLATE
from services.llm.client import DOC_DELIM_START, DOC_DELIM_END
from services.embedding import embedder
from services.storage import vector_store
from services.guardrails import validate_message, check_rate_limit, sanitize_output
from models.report import TailoringReport
from models.chat_message import ChatMessage
from schemas.chat import ChatRequest

logger = logging.getLogger(__name__)
router = APIRouter()


async def _load_history(db: AsyncSession, resume_id: UUID) -> list[dict]:
    result = await db.execute(
        select(ChatMessage.role, ChatMessage.content)
        .where(ChatMessage.resume_id == resume_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return [{"role": role, "content": content} for role, content in result.all()]


async def _save_message(
    db: AsyncSession,
    report_id: UUID,
    user_id: UUID,
    resume_id: UUID,
    role: str,
    content: str,
):
    db.add(
        ChatMessage(
            report_id=report_id,
            user_id=user_id,
            resume_id=resume_id,
            role=role,
            content=content,
        )
    )
    await db.commit()


@router.get("/chat/history/{report_id}")
async def get_chat_history(
    report_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TailoringReport.resume_id).where(
            TailoringReport.id == report_id,
            TailoringReport.user_id == user_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    history = await _load_history(db, row[0])
    return {"messages": history}


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    error = await validate_message(request.message)
    if error:
        async def err_gen():
            yield f"data: {json.dumps({'type': 'error', 'message': error})}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    redis = await get_redis()

    cache_key = f"chat:report:{request.report_id}:context"
    cached = await redis.get(cache_key)
    if cached:
        ctx = json.loads(cached)
        resume_id = request.resume_id or UUID(ctx["resume_id"])
        jd_text = ctx.get("jd_text", "")
        github_context = ctx.get("github_analysis", "")
    else:
        result = await db.execute(
            select(TailoringReport.jd_text, TailoringReport.github_analysis, TailoringReport.resume_id).where(
                TailoringReport.id == request.report_id,
                TailoringReport.user_id == user_id,
            )
        )
        row = result.one_or_none()
        if not row:
            async def err_gen():
                yield f"data: {json.dumps({'type': 'error', 'message': 'Report not found'})}\n\n"
            return StreamingResponse(err_gen(), media_type="text/event-stream")

        resume_id = request.resume_id or row[2]
        jd_text = row[0] or ""
        ga = row[1]
        github_context = json.dumps(ga, indent=2) if ga else ""
        await redis.setex(cache_key, 3600, json.dumps({
            "resume_id": str(row[2]),
            "jd_text": jd_text,
            "github_analysis": github_context,
        }))

    session_key = f"chat:{user_id}:{resume_id}"
    rate_error = await check_rate_limit(redis, session_key)
    if rate_error:
        async def err_gen():
            yield f"data: {json.dumps({'type': 'error', 'message': rate_error})}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    history = await _load_history(db, resume_id)

    query_embedding = (await asyncio.to_thread(embedder.embed_documents, [request.message]))[0]
    rag_results = await vector_store.query_by_resume(db, str(resume_id), query_embedding, top_k=5)

    rag_docs = []
    if rag_results and rag_results.get("documents") and rag_results["documents"][0]:
        rag_docs = rag_results["documents"][0]
    else:
        async def err_gen():
            yield f"data: {json.dumps({'type': 'error', 'message': 'Resume chunks not found'})}\n\n"
        return StreamingResponse(err_gen(), media_type="text/event-stream")

    context = "\n\n".join(rag_docs)

    system_parts = [CHAT_SYSTEM_PROMPT_TEMPLATE]

    if jd_text:
        system_parts.append(f"\nTarget Job Description:\n{DOC_DELIM_START}\n{jd_text}\n{DOC_DELIM_END}")
    if github_context:
        system_parts.append(f"\nGitHub Portfolio Context:\n{DOC_DELIM_START}\n{github_context}\n{DOC_DELIM_END}")
    system_parts.append(f"\nRelevant resume context:\n{DOC_DELIM_START}\n{context}\n{DOC_DELIM_END}")
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
            await _save_message(db, request.report_id, user_id, resume_id, "user", request.message)

            full_content = ""
            async for token in llm_client.stream_chat(messages):
                full_content += token
                yield f"data: {json.dumps({'type': 'text', 'content': full_content})}\n\n"

            final = sanitize_output(full_content)
            await _save_message(db, request.report_id, user_id, resume_id, "assistant", final)
            yield f"data: {json.dumps({'type': 'final', 'result': {'summary': 'Complete'}})}\n\n"

        except Exception as e:
            logger.error(f"Chat stream error: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': 'An internal error occurred. Please try again.'})}\n\n"

    return StreamingResponse(generator(), media_type="text/event-stream")
