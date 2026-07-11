import os
import sys
import json
import asyncio
import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy import select, update

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from services.db import init_db, close_db, async_session_factory
from services.redis_client import get_redis, close_redis
from services.matcher import matcher
from services.llm_service import llm_service
from models.report import TailoringReport

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] [worker] %(name)s: %(message)s",
)
logger = logging.getLogger("worker")

JOB_STREAM = "tailoring-jobs"
GROUP_NAME = "tailoring-workers"
CONSUMER_NAME = f"worker-{os.getpid()}"
MAX_RETRIES = 3
RETRY_DELAY = [1, 2, 4]


async def send_completion_email(email: str, report_id: str):
    resend_key = os.environ.get("RESEND_API_KEY", "")
    resend_from = os.environ.get("RESEND_FROM_EMAIL", "")
    if not resend_key or not resend_from:
        logger.warning("Resend not configured, skipping email")
        return

    dashboard_url = os.environ.get("DASHBOARD_URL", "http://localhost:3000")
    link = f"{dashboard_url}/dashboard/{report_id}"

    async with httpx.AsyncClient() as client:
        await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {resend_key}"},
            json={
                "from": resend_from,
                "to": [email],
                "subject": "Your Resume Analysis is Ready",
                "html": f"""
                <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; padding: 40px;">
                    <h2 style="color: #1a1a2e;">Your resume analysis is complete!</h2>
                    <p>We've analyzed your resume against the job description and prepared
                    actionable insights to help you optimize your application.</p>
                    <div style="text-align: center; margin: 30px 0;">
                        <a href="{link}"
                           style="background: #6366f1; color: white; padding: 14px 28px;
                                  text-decoration: none; border-radius: 8px; font-weight: bold;">
                            View Your Results
                        </a>
                    </div>
                    <p style="color: #666; font-size: 14px;">
                        This link expires in 24 hours.
                    </p>
                </div>
                """,
            },
        )
    logger.info(f"Completion email sent to {email}")


async def process_job(payload: dict, db):
    report_id = payload["report_id"]
    user_id = payload["user_id"]
    resume_id = payload["resume_id"]
    jd_text = payload["jd_text"]

    logger.info(f"Processing job: report={report_id}")

    # Update status -> processing
    await db.execute(
        update(TailoringReport)
        .where(TailoringReport.id == report_id)
        .values(status="processing")
    )
    await db.commit()

    try:
        # 1. Compute similarity (CPU-bound, fast)
        match_result = matcher.compute_similarity(
            job_description=jd_text,
            resume_id=resume_id,
        )
        logger.info(f"Match score: {match_result.get('final_score')}%")

        # 2. LLM calls with shared key
        api_key = os.environ.get("LLM_API_KEY", "")
        base_url = "https://api.openai.com/v1"
        model = "gpt-4o-mini"

        # Get resume text for LLM context
        stored_data = matcher.vector_store.get_by_resume(resume_id)
        resume_text = " ".join(stored_data.get("documents", []))

        # Generate report (career coach framing)
        report = await llm_service.generate_candidate_report(
            resume_text, jd_text, match_result, {}, api_key, base_url, model
        )

        # Generate interview questions (mock interview prep)
        questions = await llm_service.generate_interview_questions(
            resume_text, jd_text, match_result["missing_required"], {},
            api_key, base_url, model,
        )

        # Generate actionable rewrites (new method)
        rewrites = await llm_service.generate_actionable_rewrites(
            match_result.get("low_scoring_chunks", []),
            jd_text,
            api_key, base_url, model,
        )

        # 3. Save results to Postgres
        await db.execute(
            update(TailoringReport)
            .where(TailoringReport.id == report_id)
            .values(
                status="completed",
                match_result=match_result,
                report=report,
                questions=questions,
                rewrites=rewrites,
                completed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        logger.info(f"Job completed: report={report_id}")

        # 4. Send email with magic link
        from models.user import User
        user_result = await db.execute(select(User.email).where(User.id == user_id))
        email = user_result.scalar_one_or_none()
        if email:
            await send_completion_email(email, report_id)

    except Exception as e:
        logger.error(f"Job failed: report={report_id}, error={e}")
        await db.execute(
            update(TailoringReport)
            .where(TailoringReport.id == report_id)
            .values(
                status="failed",
                error_message=str(e),
                completed_at=datetime.now(timezone.utc),
            )
        )
        await db.commit()
        raise


async def ensure_consumer_group(redis):
    try:
        await redis.xgroup_create(JOB_STREAM, GROUP_NAME, id="0", mkstream=True)
        logger.info(f"Consumer group '{GROUP_NAME}' created")
    except Exception:
        pass  # Group already exists


async def main():
    logger.info("Starting worker...")
    await init_db()
    redis = await get_redis()
    await ensure_consumer_group(redis)

    logger.info(f"Listening on stream '{JOB_STREAM}' as '{CONSUMER_NAME}'")

    while True:
        try:
            entries = await redis.xreadgroup(
                groupname=GROUP_NAME,
                consumername=CONSUMER_NAME,
                streams={JOB_STREAM: ">"},
                count=1,
                block=5000,
            )

            if not entries:
                continue

            for stream_name, messages in entries:
                for msg_id, data in messages:
                    payload_str = data.get("payload", "{}")
                    payload = json.loads(payload_str)

                    retries = int(data.get("retries", 0))

                    try:
                        async with async_session_factory() as db:
                            await process_job(payload, db)
                        await redis.xack(JOB_STREAM, GROUP_NAME, msg_id)

                    except Exception as e:
                        logger.error(f"Attempt {retries + 1} failed: {e}")
                        if retries < MAX_RETRIES - 1:
                            await redis.xadd(
                                JOB_STREAM,
                                {**data, "retries": str(retries + 1)},
                            )
                        else:
                            logger.error(f"Max retries reached for {msg_id}")
                        await redis.xack(JOB_STREAM, GROUP_NAME, msg_id)

        except asyncio.CancelledError:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await asyncio.sleep(1)

    await close_db()
    await close_redis()
    logger.info("Worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
