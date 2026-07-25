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
from services.guardrails.pii import scrub_pii
from services.pdf import generate_report_pdf
from services.integrations.brevo import brevo_email
from services.cleanup import purger
from models.report import TailoringReport
from models.user import User

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [worker] %(name)s: %(message)s")
logger = logging.getLogger("worker")

LAST_ID_KEY = "worker:last_stream_id"
CLEANUP_INTERVAL = 100


async def process_job(payload: dict, db, redis):
    report_id = payload["report_id"]

    result = await db.execute(
        select(TailoringReport.status).where(TailoringReport.id == report_id)
    )
    row = result.one_or_none()
    if row and row[0] in ("completed", "failed"):
        logger.info(f"Skipping already {row[0]} report={report_id}")
        return

    logger.info(f"Processing job: report={report_id}")

    await db.execute(
        update(TailoringReport).where(TailoringReport.id == report_id).values(status="processing")
    )
    await db.commit()

    try:
        match_result = await matcher.compute_similarity(db, payload["jd_text"], payload["resume_id"], redis=redis)
        logger.info(f"Match score: {match_result.get('final_score')}%")

        resume_text = await vector_store.get_resume_text(db, payload["resume_id"])
        clean_resume = scrub_pii(resume_text)

        logger.info(f"Generating report for: report={report_id}")
        report = await llm_client.generate_candidate_report(clean_resume, payload["jd_text"], match_result, {})
        logger.info(f"Generating questions for: report={report_id}")
        questions = await llm_client.generate_interview_questions(
            clean_resume, payload["jd_text"], match_result["missing_required"], {}
        )
        logger.info(f"Generating rewrites for: report={report_id}")
        rewrites = await llm_client.generate_actionable_rewrites(
            match_result.get("low_scoring_chunks", []), payload["jd_text"]
        )
        logger.info(f"LLM calls complete for: report={report_id}")

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
            await redis.publish(f"report:{report_id}", json.dumps({"status": "completed"}))
        except Exception as pub_err:
            logger.warning(f"Failed to publish completion event: {pub_err}")

        if payload.get("send_email"):
            try:
                user_result = await db.execute(select(User.email).where(User.id == payload["user_id"]))
                user_email = user_result.scalar_one_or_none()
                if user_email:
                    pdf_bytes = generate_report_pdf(
                        match_result=match_result,
                        report=report,
                        questions=questions,
                        rewrites=rewrites,
                        jd_text=payload.get("jd_text", ""),
                    )
                    from config.settings import settings
                    dashboard_url = f"{settings.cors_origin_list[0] if settings.cors_origin_list else 'http://localhost:5173'}/dashboard/{report_id}"
                    await brevo_email.send_report_notification(
                        to_email=user_email,
                        score=match_result.get("final_score", 0),
                        report_id=report_id,
                        dashboard_url=dashboard_url,
                        pdf_bytes=pdf_bytes,
                    )
            except Exception as email_err:
                logger.error(f"Failed to send report email: {email_err}")

    except Exception as e:
        logger.error(f"Job failed: report={report_id}, error={e}")
        try:
            await db.rollback()
            async with db_module.async_session_factory() as fresh_db:
                await fresh_db.execute(
                    update(TailoringReport)
                    .where(TailoringReport.id == report_id)
                    .values(status="failed", error_message=str(e)[:500], completed_at=datetime.now(timezone.utc))
                )
                await fresh_db.commit()
        except Exception as update_err:
            logger.error(f"Failed to mark report as failed: {update_err}")
        try:
            await redis.publish(f"report:{report_id}", json.dumps({"status": "failed"}))
        except Exception:
            pass
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

    last_id_raw = await redis.get(LAST_ID_KEY)
    if last_id_raw:
        LAST_ID = last_id_raw.decode() if isinstance(last_id_raw, bytes) else str(last_id_raw)
        logger.info(f"Resumed from stream position: {LAST_ID}")
    else:
        LAST_ID = "$"
        logger.info("No saved position — starting from latest stream entry, trimming old messages")
        try:
            await redis.delete(WORKER_STREAM_NAME)
            logger.info("Flushed stale stream entries")
        except Exception:
            pass

    try:
        await redis.xtrim(WORKER_STREAM_NAME, maxlen=50)
        logger.info("Trimmed stream on startup")
    except Exception:
        pass

    logger.info(f"Listening on stream '{WORKER_STREAM_NAME}' with xread (no consumer group)")

    poll_count = 0
    while True:
        try:
            entries = await redis.xread({WORKER_STREAM_NAME: LAST_ID}, count=1)

            if not entries:
                poll_count += 1
                if poll_count >= CLEANUP_INTERVAL:
                    poll_count = 0
                    try:
                        async with db_module.async_session_factory() as db:
                            result = await purger.run_cleanup(db)
                            if any(v > 0 for v in result.values()):
                                logger.info(f"Cleanup: {result}")
                    except Exception as cleanup_err:
                        logger.error(f"Cleanup failed: {cleanup_err}")
                await asyncio.sleep(10)
                continue

            for stream_name, messages in entries:
                for msg_id, raw_fields in messages:
                    data = parse_entry(raw_fields)
                    logger.info(f"Received job: msg_id={msg_id}, data={data}")
                    LAST_ID = msg_id
                    try:
                        await redis.set(LAST_ID_KEY, msg_id)
                    except Exception:
                        pass

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

                    try:
                        await redis.xtrim(WORKER_STREAM_NAME, maxlen=50)
                    except Exception:
                        pass

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
