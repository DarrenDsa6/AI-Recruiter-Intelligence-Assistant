import json
import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from core.dependencies import get_current_user
from services.database import get_db
import services.database as db_module
from services.redis import get_redis
from services.parsing.classifier import classify_document
from services.guardrails import validate_jd_text
from models.report import TailoringReport
from models.resume import MasterResume
from models.user import User
from models.chunk import ResumeChunk
from schemas.match import MatchRequest, MatchAccepted
from config.constants import RATE_LIMIT_MATCHES_MAX, RATE_LIMIT_MATCHES_WINDOW_SECONDS, WORKER_STREAM_URGENT, WORKER_STREAM_EMAIL

MAX_REPORTS_PER_USER = 3

logger = logging.getLogger(__name__)
router = APIRouter()


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
    pipe = redis.pipeline()
    pipe.incr(rate_key)
    pipe.expire(rate_key, RATE_LIMIT_MATCHES_WINDOW_SECONDS)
    results = await pipe.exec()
    count = results[0]
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
    job_stream = WORKER_STREAM_EMAIL if body.send_email else WORKER_STREAM_URGENT
    entry_id = await redis.xadd(job_stream, "*", {"payload": job_payload})
    logger.info(f"Stream entry id: {entry_id} (stream={job_stream})")

    logger.info(f"Job queued: report={report.id} resume={body.resume_id}")

    await _purge_old_reports(db, user_id)

    return MatchAccepted(report_id=report.id)


async def _purge_old_reports(db: AsyncSession, user_id: UUID):
    try:
        result = await db.execute(
            select(TailoringReport.id)
            .where(TailoringReport.user_id == user_id)
            .order_by(TailoringReport.created_at.desc())
            .offset(MAX_REPORTS_PER_USER)
        )
        old_ids = [row[0] for row in result.all()]
        if not old_ids:
            return

        chunk_del = await db.execute(
            delete(ResumeChunk).where(
                ResumeChunk.resume_id.in_(
                    select(TailoringReport.resume_id).where(TailoringReport.id.in_(old_ids))
                )
            )
        )
        await db.execute(delete(TailoringReport).where(TailoringReport.id.in_(old_ids)))
        await db.commit()
        logger.info(f"Purged {len(old_ids)} old reports for user {user_id} ({chunk_del.rowcount} chunks)")
    except Exception as e:
        logger.error(f"Failed to purge old reports: {e}")
        await db.rollback()


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
    resume_ids = [r.resume_id for r in reports]
    if resume_ids:
        resume_result = await db.execute(
            select(MasterResume.id, MasterResume.filename).where(MasterResume.id.in_(resume_ids))
        )
        filename_map = {row[0]: row[1] for row in resume_result.all()}
    else:
        filename_map = {}
    for r in reports:
        items.append({
            "id": r.id,
            "resume_id": r.resume_id,
            "status": r.status,
            "jd_text": r.jd_text[:100] + "..." if len(r.jd_text) > 100 else r.jd_text,
            "filename": filename_map.get(r.resume_id),
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
        "resume_id": report.resume_id,
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

    async def poll_status():
        max_polls = 150
        polls = 0
        while polls < max_polls:
            await asyncio.sleep(2)
            polls += 1
            async with db_module.async_session_factory() as poll_db:
                result = await poll_db.execute(
                    select(TailoringReport.status).where(
                        TailoringReport.id == report_id,
                        TailoringReport.user_id == user_id,
                    )
                )
                status = result.scalar_one_or_none()
                if status in ("completed", "failed"):
                    yield f"data: {json.dumps({'status': status})}\n\n"
                    return
        yield f"data: {json.dumps({'status': 'timeout'})}\n\n"

    return StreamingResponse(poll_status(), media_type="text/event-stream")


@router.delete("/reports/{report_id}")
async def delete_report(
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

    resume_id = report.resume_id
    await db.execute(delete(ResumeChunk).where(ResumeChunk.resume_id == resume_id))
    await db.execute(delete(TailoringReport).where(TailoringReport.id == report_id))
    await db.commit()
    return {"message": "Report deleted"}


@router.post("/reports/{report_id}/send-email")
async def send_report_email(
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
    if report.status != "completed":
        raise HTTPException(status_code=400, detail="Report is not completed yet")

    user_result = await db.execute(select(User.email).where(User.id == user_id))
    user_email = user_result.scalar_one_or_none()
    if not user_email:
        raise HTTPException(status_code=400, detail="No email found for user")

    try:
        from services.pdf import generate_report_pdf
        from services.integrations.brevo import brevo_email
        from config.settings import settings

        pdf_bytes = generate_report_pdf(
            match_result=report.match_result or {},
            report=report.report or {},
            questions=report.questions or {},
            rewrites=report.rewrites or {},
            jd_text=report.jd_text or "",
        )
        score = (report.match_result or {}).get("final_score", 0)
        dashboard_url = f"{settings.cors_origin_list[0] if settings.cors_origin_list else 'http://localhost:3000'}/dashboard/{report_id}"
        await brevo_email.send_report_notification(
            to_email=user_email,
            score=score,
            report_id=report_id,
            dashboard_url=dashboard_url,
            pdf_bytes=pdf_bytes,
        )
        return {"message": "Report sent to your email"}
    except Exception as e:
        logger.error(f"Failed to send report email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email")
