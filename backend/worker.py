import json
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import select, update

sys.path.insert(0, os.path.dirname(__file__))

from config.constants import WORKER_STREAM_NAME, WORKER_CONSUMER_GROUP, WORKER_MAX_RETRIES
from services.database import init_db, close_db, async_session_factory
from services.redis import get_redis, close_redis
from services.matching import matcher
from services.llm import llm_client
from services.storage import vector_store
from services.integrations.brevo import brevo_email
from models.report import TailoringReport
from models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [worker] %(name)s: %(message)s")
logger = logging.getLogger("worker")

CONSUMER_NAME = f"worker-{os.getpid()}"


async def process_job(payload: dict, db, redis):
    report_id = payload["report_id"]

    logger.info(f"Processing job: report={report_id}")

    await db.execute(
        update(TailoringReport).where(TailoringReport.id == report_id).values(status="processing")
    )
    await db.commit()

    try:
        match_result = await matcher.compute_similarity(db, payload["jd_text"], payload["resume_id"], redis=redis)
        logger.info(f"Match score: {match_result.get('final_score')}%")

        resume_text = await vector_store.get_resume_text(db, payload["resume_id"])

        report = await llm_client.generate_candidate_report(resume_text, payload["jd_text"], match_result, {})
        questions = await llm_client.generate_interview_questions(
            resume_text, payload["jd_text"], match_result["missing_required"], {}
        )
        rewrites = await llm_client.generate_actionable_rewrites(
            match_result.get("low_scoring_chunks", []), payload["jd_text"]
        )

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

        try:
            user_result = await db.execute(select(User.email).where(User.id == payload["user_id"]))
            user_email = user_result.scalar_one_or_none()
            if user_email:
                from config.settings import settings
                dashboard_url = f"{settings.cors_origin_list[0] if settings.cors_origin_list else 'http://localhost:5173'}/dashboard/{report_id}"
                await brevo_email.send_report_notification(
                    to_email=user_email,
                    score=match_result.get("final_score", 0),
                    report_id=report_id,
                    dashboard_url=dashboard_url,
                )
        except Exception as email_err:
            logger.error(f"Failed to send report email: {email_err}")

    except Exception as e:
        logger.error(f"Job failed: report={report_id}, error={e}")
        await db.execute(
            update(TailoringReport)
            .where(TailoringReport.id == report_id)
            .values(status="failed", error_message=str(e), completed_at=datetime.now(timezone.utc))
        )
        await db.commit()
        raise


async def ensure_consumer_group(redis):
    try:
        await redis.xgroup_create(WORKER_STREAM_NAME, WORKER_CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(f"Consumer group '{WORKER_CONSUMER_GROUP}' created")
    except Exception:
        pass


async def main():
    logger.info("Starting worker...")
    await init_db()
    redis = await get_redis()
    await ensure_consumer_group(redis)

    logger.info(f"Listening on stream '{WORKER_STREAM_NAME}' as '{CONSUMER_NAME}'")

    while True:
        try:
            entries = await redis.xreadgroup(
                groupname=WORKER_CONSUMER_GROUP,
                consumername=CONSUMER_NAME,
                streams={WORKER_STREAM_NAME: ">"},
                count=1,
                block=5000,
            )

            if not entries:
                continue

            for stream_name, messages in entries:
                for msg_id, data in messages:
                    payload = json.loads(data.get("payload", "{}"))
                    retries = int(data.get("retries", 0))

                    try:
                        async with async_session_factory() as db:
                            await process_job(payload, db, redis)
                        await redis.xack(WORKER_STREAM_NAME, WORKER_CONSUMER_GROUP, msg_id)
                    except Exception as e:
                        logger.error(f"Attempt {retries + 1} failed: {e}")
                        if retries < WORKER_MAX_RETRIES - 1:
                            await redis.xadd(WORKER_STREAM_NAME, data={**data, "retries": str(retries + 1)})
                        else:
                            logger.error(f"Max retries reached for {msg_id}")
                        await redis.xack(WORKER_STREAM_NAME, WORKER_CONSUMER_GROUP, msg_id)

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
