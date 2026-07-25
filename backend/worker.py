import json
import asyncio
import logging
import os
import sys
from datetime import datetime, timezone

from sqlalchemy import select, update

sys.path.insert(0, os.path.dirname(__file__))

from config.constants import WORKER_STREAM_URGENT, WORKER_STREAM_EMAIL, WORKER_MAX_RETRIES
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

LAST_ID_KEY_URGENT = "worker:last_stream_id:urgent"
LAST_ID_KEY_EMAIL = "worker:last_stream_id:email"
CLEANUP_INTERVAL = 100
WORKER_CONCURRENCY = 3

LAST_ID_URGENT = "0"
LAST_ID_EMAIL = "0"


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
        raise


def parse_entry(raw_fields):
    if isinstance(raw_fields, dict):
        return raw_fields
    if isinstance(raw_fields, list):
        return dict(zip(raw_fields[::2], raw_fields[1::2]))
    return {}


async def main():
    global LAST_ID_URGENT, LAST_ID_EMAIL
    logger.info(f"Starting worker (concurrency={WORKER_CONCURRENCY})...")
    await init_db()
    redis = await get_redis()

    for key, name, var_attr in [
        (LAST_ID_KEY_URGENT, "urgent", "urgent"),
        (LAST_ID_KEY_EMAIL, "email", "email"),
    ]:
        saved = await redis.get(key)
        if saved:
            val = saved.decode() if isinstance(saved, bytes) else str(saved)
            if var_attr == "urgent":
                LAST_ID_URGENT = val
            else:
                LAST_ID_EMAIL = val
            logger.info(f"Resumed {name} stream from position: {val}")
        else:
            if var_attr == "urgent":
                LAST_ID_URGENT = "$"
            else:
                LAST_ID_EMAIL = "$"
            logger.info(f"No saved position for {name} stream — starting from latest")

    try:
        await redis.xtrim(WORKER_STREAM_URGENT, maxlen=50)
        await redis.xtrim(WORKER_STREAM_EMAIL, maxlen=50)
        logger.info("Trimmed streams on startup")
    except Exception:
        pass

    semaphore = asyncio.Semaphore(WORKER_CONCURRENCY)
    active_tasks: set[asyncio.Task] = set()

    async def run_job(payload, is_urgent, retries):
        async with semaphore:
            try:
                async with db_module.async_session_factory() as db:
                    await process_job(payload, db, redis)
            except Exception as e:
                logger.error(f"Attempt {retries + 1} failed: {e}")
                if retries < WORKER_MAX_RETRIES - 1:
                    retry_payload = json.dumps({**payload, "retries": retries + 1})
                    retry_stream = WORKER_STREAM_URGENT if is_urgent else WORKER_STREAM_EMAIL
                    await redis.xadd(retry_stream, "*", {"payload": retry_payload})
                else:
                    logger.error(f"Max retries reached for report={payload.get('report_id')}")

    logger.info(f"Listening on '{WORKER_STREAM_URGENT}' (priority) and '{WORKER_STREAM_EMAIL}' (email)")

    poll_count = 0
    while True:
        try:
            entries = await redis.xread(
                {WORKER_STREAM_URGENT: LAST_ID_URGENT, WORKER_STREAM_EMAIL: LAST_ID_EMAIL},
                count=1,
            )

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
                    is_urgent = stream_name == WORKER_STREAM_URGENT
                    logger.info(f"Received job: msg_id={msg_id}, stream={'urgent' if is_urgent else 'email'}, active={len(active_tasks)}")

                    if is_urgent:
                        LAST_ID_URGENT = msg_id
                        try:
                            await redis.set(LAST_ID_KEY_URGENT, msg_id)
                        except Exception:
                            pass
                    else:
                        LAST_ID_EMAIL = msg_id
                        try:
                            await redis.set(LAST_ID_KEY_EMAIL, msg_id)
                        except Exception:
                            pass

                    try:
                        raw_payload = data.get("payload", "{}")
                        if isinstance(raw_payload, bytes):
                            raw_payload = raw_payload.decode("utf-8")
                        payload = json.loads(raw_payload)
                        retries = int(data.get("retries", 0))
                    except Exception as parse_err:
                        logger.error(f"Failed to parse entry: {parse_err}")
                        continue

                    task = asyncio.create_task(run_job(payload, is_urgent, retries))
                    active_tasks.add(task)
                    task.add_done_callback(active_tasks.discard)

            try:
                await redis.xtrim(WORKER_STREAM_URGENT, maxlen=50)
                await redis.xtrim(WORKER_STREAM_EMAIL, maxlen=50)
            except Exception:
                pass

        except asyncio.CancelledError:
            logger.info("Worker shutting down...")
            break
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            await asyncio.sleep(5)

    if active_tasks:
        logger.info(f"Waiting for {len(active_tasks)} active jobs to finish...")
        await asyncio.gather(*active_tasks, return_exceptions=True)

    await close_db()
    await close_redis()
    logger.info("Worker stopped")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrupted")
