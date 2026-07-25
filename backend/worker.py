import json
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import select, update

sys.path.insert(0, os.path.dirname(__file__))

from config.constants import WORKER_STREAM_NAME, WORKER_MAX_RETRIES
from services.database import init_db, close_db
import services.database as db_module
from services.redis import get_redis, close_redis
from services.matching import matcher
from services.llm import llm_client
from services.storage import vector_store
from services.integrations.brevo import brevo_email
from models.report import TailoringReport
from models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [worker] %(name)s: %(message)s")
logger = logging.getLogger("worker")

LAST_ID = "0"


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


def parse_entry(raw_fields):
    if isinstance(raw_fields, dict):
        return raw_fields
    if isinstance(raw_fields, list):
        return dict(zip(raw_fields[::2], raw_fields[1::2]))
    return {}


async def main():
    global LAST_ID
    logger.info("Starting worker...")
    await init_db()
    redis = await get_redis()

    logger.info(f"Listening on stream '{WORKER_STREAM_NAME}' with xread (no consumer group)")

    while True:
        try:
            entries = await redis.xread({WORKER_STREAM_NAME: LAST_ID}, count=1)

            if not entries:
                await asyncio.sleep(10)
                continue

            for stream_name, messages in entries:
                for msg_id, raw_fields in messages:
                    data = parse_entry(raw_fields)
                    logger.info(f"Received job: msg_id={msg_id}, data={data}")
                    LAST_ID = msg_id

                    try:
                        raw_payload = data.get("payload", "{}")
                        if isinstance(raw_payload, bytes):
                            raw_payload = raw_payload.decode("utf-8")
                        payload = json.loads(raw_payload)
                        retries = int(data.get("retries", 0))
                    except Exception as parse_err:
                        logger.error(f"Failed to parse entry: {parse_err}, raw_fields={raw_fields}")
                        continue

                    try:
                        async with db_module.async_session_factory() as db:
                            await process_job(payload, db, redis)
                    except Exception as e:
                        logger.error(f"Attempt {retries + 1} failed: {e}")
                        if retries < WORKER_MAX_RETRIES - 1:
                            retry_payload = json.dumps({**payload, "retries": retries + 1})
                            await redis.xadd(WORKER_STREAM_NAME, "*", {"payload": retry_payload})
                        else:
                            logger.error(f"Max retries reached for report={payload.get('report_id')}")

        except asyncio.CancelledError:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await asyncio.sleep(5)

    await close_db()
    await close_redis()
    logger.info("Worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
