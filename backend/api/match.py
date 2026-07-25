import json
import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
from services.redis import get_redis
from services.parsing.classifier import classify_document
from services.guardrails import validate_jd_text
from models.report import TailoringReport
from models.resume import MasterResume
from schemas.match import MatchRequest, MatchAccepted
from config.constants import RATE_LIMIT_MATCHES_MAX, RATE_LIMIT_MATCHES_WINDOW_SECONDS

logger = logging.getLogger(__name__)
router = APIRouter()

JOB_STREAM = "tailoring-jobs"


@router.post("/match", response_model=MatchAccepted, status_code=202)
async def match_job_description(
    body: MatchRequest,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    jd_guardrail_error = validate_jd_text(body.jd_text, user_id)
    if jd_guardrail_error:
        raise HTTPException(status_code=422, detail=jd_guardrail_error)

    redis = await get_redis()
    rate_key = f"match_rate:{user_id}"
    count = await redis.incr(rate_key)
    if count == 1:
        await redis.expire(rate_key, RATE_LIMIT_MATCHES_WINDOW_SECONDS)
    if count > RATE_LIMIT_MATCHES_MAX:
        raise HTTPException(
            status_code=429,
            detail=f"Daily match limit reached ({RATE_LIMIT_MATCHES_MAX}). Try again tomorrow.",
        )

    classification = await classify_document(body.jd_text)
    logger.info(
        f"JD classified as {classification.doc_type} "
        f"(confidence={classification.confidence:.2f}, tier={classification.tier})"
    )
    if classification.doc_type == "resume" and classification.confidence >= 0.85:
        raise HTTPException(
            status_code=422,
            detail="The text provided appears to be a resume, not a job description.",
        )

    result = await db.execute(
        select(MasterResume).where(
            MasterResume.id == body.resume_id,
            MasterResume.user_id == user_id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        raise HTTPException(status_code=404, detail="Resume not found")

    report = TailoringReport(
        user_id=user_id,
        resume_id=body.resume_id,
        jd_text=body.jd_text,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    job_payload = json.dumps({
        "report_id": str(report.id),
        "user_id": str(user_id),
        "resume_id": str(body.resume_id),
        "jd_text": body.jd_text,
        "send_email": body.send_email,
    })
    entry_id = await redis.xadd(JOB_STREAM, "*", {"payload": job_payload})
    logger.info(f"Stream entry id: {entry_id}")

    logger.info(f"Job queued: report={report.id} resume={body.resume_id}")
    return MatchAccepted(report_id=report.id)


@router.get("/reports")
async def list_reports(
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TailoringReport)
        .where(TailoringReport.user_id == user_id)
        .order_by(TailoringReport.created_at.desc())
    )
    reports = result.scalars().all()

    items = []
    for r in reports:
        resume_result = await db.execute(
            select(MasterResume.filename).where(MasterResume.id == r.resume_id)
        )
        filename = resume_result.scalar_one_or_none()
        items.append({
            "id": r.id,
            "status": r.status,
            "jd_text": r.jd_text[:100] + "..." if len(r.jd_text) > 100 else r.jd_text,
            "filename": filename,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "completed_at": r.completed_at.isoformat() if r.completed_at else None,
        })
    return items


@router.get("/reports/{report_id}")
async def get_report(
    report_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TailoringReport).where(
            TailoringReport.id == report_id,
            TailoringReport.user_id == user_id,
        )
    )
    report = result.scalar_one_or_none()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    return {
        "id": report.id,
        "status": report.status,
        "jd_text": report.jd_text,
        "match_result": report.match_result,
        "github_analysis": report.github_analysis,
        "report": report.report,
        "questions": report.questions,
        "rewrites": report.rewrites,
        "error_message": report.error_message,
        "created_at": report.created_at.isoformat() if report.created_at else None,
        "completed_at": report.completed_at.isoformat() if report.completed_at else None,
    }


@router.get("/reports/{report_id}/status")
async def get_report_status(
    report_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TailoringReport.id, TailoringReport.status).where(
            TailoringReport.id == report_id,
            TailoringReport.user_id == user_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    return {"id": row[0], "status": row[1]}


@router.get("/reports/{report_id}/stream")
async def stream_report_status(
    report_id: UUID,
    user_id: UUID = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TailoringReport.id, TailoringReport.status).where(
            TailoringReport.id == report_id,
            TailoringReport.user_id == user_id,
        )
    )
    row = result.one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")

    if row[1] in ("completed", "failed"):
        async def immediate():
            yield f"data: {json.dumps({'status': row[1]})}\n\n"
        return StreamingResponse(immediate(), media_type="text/event-stream")

    async def subscribe():
        redis = await get_redis()
        pubsub = redis.pubsub()
        channel = f"report:{report_id}"
        await pubsub.subscribe(channel)
        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    data = json.loads(message["data"])
                    yield f"data: {json.dumps(data)}\n\n"
                    if data.get("status") in ("completed", "failed"):
                        break
        finally:
            await pubsub.unsubscribe(channel)
            await pubsub.close()

    return StreamingResponse(subscribe(), media_type="text/event-stream")
