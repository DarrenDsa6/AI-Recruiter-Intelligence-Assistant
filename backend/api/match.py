import json
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.redis_client import get_redis
from services.db import get_db
from models.report import TailoringReport
from schemas.match import MatchRequest, MatchAccepted
from schemas.common import ErrorResponse

logger = logging.getLogger(__name__)
router = APIRouter()

JOB_STREAM = "tailoring-jobs"


async def _get_user_id(authorization: str = Header(...)) -> UUID:
    import jwt
    import os
    token = authorization.replace("Bearer ", "")
    payload = jwt.decode(token, os.environ.get("JWT_SECRET", ""), algorithms=["HS256"])
    return UUID(payload["sub"])


@router.post("/match", response_model=MatchAccepted, status_code=202)
async def match_job_description(
    body: MatchRequest,
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    # Validate resume exists for this user
    from models.resume import MasterResume
    result = await db.execute(
        select(MasterResume).where(
            MasterResume.id == body.resume_id,
            MasterResume.user_id == user_id,
        )
    )
    resume = result.scalar_one_or_none()
    if not resume:
        return ErrorResponse(error="Resume not found")

    # Create report record
    report = TailoringReport(
        user_id=user_id,
        resume_id=body.resume_id,
        jd_text=body.jd_text,
        status="pending",
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)

    # Push job to Redis Stream
    redis = await get_redis()
    job_payload = json.dumps({
        "report_id": str(report.id),
        "user_id": str(user_id),
        "resume_id": str(body.resume_id),
        "jd_text": body.jd_text,
    })
    await redis.xadd(JOB_STREAM, {"payload": job_payload})

    logger.info(f"Job queued: report={report.id} resume={body.resume_id}")

    return MatchAccepted(report_id=report.id)


@router.get("/reports")
async def list_reports(
    user_id: UUID = Depends(_get_user_id),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(TailoringReport)
        .where(TailoringReport.user_id == user_id)
        .order_by(TailoringReport.created_at.desc())
    )
    reports = result.scalars().all()

    from models.resume import MasterResume
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
    user_id: UUID = Depends(_get_user_id),
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
        return ErrorResponse(error="Report not found")

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
    user_id: UUID = Depends(_get_user_id),
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
        return ErrorResponse(error="Report not found")

    return {"id": row[0], "status": row[1]}
