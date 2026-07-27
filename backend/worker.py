import json
import asyncio
import logging
import os
import platform
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

CONSUMER_GROUP = "ai-recruiter"
CONSUMER_NAME = f"worker-{platform.node()}-{os.getpid()}"
CLEANUP_INTERVAL = 100
WORKER_CONCURRENCY = 3


async def process_job(payload: dict, db, redis):
    report_id = payload.get("report_id")
    retries = int(payload.get("retries", 0))
    if not report_id:
        logger.error("Job payload missing 'report_id', skipping")
        return

    result = await db.execute(
        select(TailoringReport.status).where(TailoringReport.id == report_id)
    )
    row = result.one_or_none()
    if row and row[0] == "completed":
        logger.info(f"Skipping already completed report={report_id}")
        return
    if row and row[0] == "failed" and retries < WORKER_MAX_RETRIES:
        logger.info(f"Retrying previously failed report={report_id} (attempt {retries + 1})")

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
        error_msg = "An internal error occurred during processing."
        if retries >= WORKER_MAX_RETRIES - 1:
            try:
                await db.rollback()
                async with db_module.async_session_factory() as fresh_db:
                    await fresh_db.execute(
                        update(TailoringReport)
                        .where(TailoringReport.id == report_id)
                        .values(status="failed", error_message=error_msg, completed_at=datetime.now(timezone.utc))
                    )
                    await fresh_db.commit()
            except Exception as update_err:
                logger.error(f"Failed to mark report as failed: {update_err}")
        else:
            try:
                await db.rollback()
            except Exception:
                pass
        raise


def parse_entry(raw_fields):
    if isinstance(raw_fields, dict):
        return raw_fields
    if isinstance(raw_fields, list):
        return dict(zip(raw_fields[::2], raw_fields[1::2]))
    return {}


def parse_payload(data):
    raw_payload = data.get("payload", "{}")
    if isinstance(raw_payload, bytes):
        raw_payload = raw_payload.decode("utf-8")
    payload = json.loads(raw_payload)
    retries = int(payload.get("retries", 0))
    if "report_id" not in payload:
        raise ValueError("Payload missing 'report_id'")
    return payload, retries


async def ensure_consumer_group(redis, stream_name):
    try:
        await redis.xgroup_create(stream_name, CONSUMER_GROUP, id="0", mkstream=True)
        logger.info(f"Created consumer group '{CONSUMER_GROUP}' on '{stream_name}'")
    except Exception as e:
        if "BUSYGROUP" not in str(e):
            raise
        logger.debug(f"Consumer group '{CONSUMER_GROUP}' already exists on '{stream_name}'")


async def recover_pending(redis, stream_name, semaphore, active_tasks, is_urgent):
    try:
        info = await redis.xpending(stream_name, CONSUMER_GROUP)
        pending_count = info[0] if isinstance(info, (list, tuple)) else 0
        if not pending_count:
            return

        logger.info(f"Found {pending_count} pending entries in {stream_name}")

        pending_detail = await redis.xpending_range(
            stream_name, CONSUMER_GROUP, min="-", max="+", count=10
        )
        if not pending_detail:
            return

        ids_to_claim = []
        for entry in pending_detail:
            msg_id = entry[0] if isinstance(entry, (list, tuple)) else entry.get("message_id")
            if msg_id:
                ids_to_claim.append(msg_id)

        if not ids_to_claim:
            return

        claimed = await redis.xclaim(
            stream_name, CONSUMER_GROUP, CONSUMER_NAME,
            min_idle_time=60000, ids=ids_to_claim
        )
        if not claimed:
            return

        for entry in claimed:
            msg_id = entry[0] if isinstance(entry, (list, tuple)) else entry.get("message_id")
            raw_fields = entry[1] if isinstance(entry, (list, tuple)) and len(entry) > 1 else entry.get("fields")
            if not msg_id or not raw_fields:
                continue

            logger.info(f"Recovered pending entry: msg_id={msg_id}, stream={stream_name}")
            data = parse_entry(raw_fields)
            payload, retries = parse_payload(data)

            task = asyncio.create_task(run_with_ack(
                payload, is_urgent, retries, redis, stream_name, msg_id, semaphore
            ))
            active_tasks.add(task)
            task.add_done_callback(active_tasks.discard)
    except Exception as e:
        logger.warning(f"Pending recovery skipped for {stream_name}: {e}")


async def run_with_ack(payload, is_urgent, retries, redis, stream_name, msg_id, semaphore):
    async with semaphore:
        try:
            async with db_module.async_session_factory() as db:
                await process_job(payload, db, redis)
            await redis.xack(stream_name, CONSUMER_GROUP, msg_id)
            logger.debug(f"ACKed msg_id={msg_id}")
        except Exception as e:
            logger.error(f"Attempt {retries + 1} failed: {e}")
            if retries < WORKER_MAX_RETRIES - 1:
                retry_payload = json.dumps({**payload, "retries": retries + 1})
                retry_stream = WORKER_STREAM_URGENT if is_urgent else WORKER_STREAM_EMAIL
                new_id = await redis.xadd(retry_stream, "*", {"payload": retry_payload})
                await redis.xack(stream_name, CONSUMER_GROUP, msg_id)
                logger.info(f"Retried as msg_id={new_id}")
            else:
                await redis.xack(stream_name, CONSUMER_GROUP, msg_id)
                logger.error(f"Max retries reached for report={payload.get('report_id')}")


async def read_stream(redis, stream_name, count=1):
    try:
        result = await redis.xreadgroup(
            CONSUMER_GROUP, CONSUMER_NAME,
            {stream_name: ">"}, count=count
        )
        if not result:
            return []
        for s_name, messages in result:
            if s_name == stream_name:
                return messages
    except Exception as e:
        logger.error(f"XREADGROUP failed for {stream_name}: {e}")
    return []


async def main():
    logger.info(f"Starting worker (concurrency={WORKER_CONCURRENCY}, group={CONSUMER_GROUP})...")
    await init_db()
    redis = await get_redis()

    await ensure_consumer_group(redis, WORKER_STREAM_URGENT)
    await ensure_consumer_group(redis, WORKER_STREAM_EMAIL)

    semaphore = asyncio.Semaphore(WORKER_CONCURRENCY)
    active_tasks: set[asyncio.Task] = set()

    logger.info(f"Checking for pending entries...")
    await recover_pending(redis, WORKER_STREAM_URGENT, semaphore, active_tasks, is_urgent=True)
    await recover_pending(redis, WORKER_STREAM_EMAIL, semaphore, active_tasks, is_urgent=False)

    logger.info(f"Listening on '{WORKER_STREAM_URGENT}' (priority) and '{WORKER_STREAM_EMAIL}' (email)")

    poll_count = 0
    while True:
        try:
            urgent_entries = await read_stream(redis, WORKER_STREAM_URGENT)
            if urgent_entries:
                for msg_id, raw_fields in urgent_entries:
                    data = parse_entry(raw_fields)
                    payload, retries = parse_payload(data)
                    logger.info(f"Received urgent job: msg_id={msg_id}, active={len(active_tasks)}")

                    task = asyncio.create_task(run_with_ack(
                        payload, True, retries, redis, WORKER_STREAM_URGENT, msg_id, semaphore
                    ))
                    active_tasks.add(task)
                    task.add_done_callback(active_tasks.discard)

            email_entries = await read_stream(redis, WORKER_STREAM_EMAIL)
            if email_entries:
                for msg_id, raw_fields in email_entries:
                    data = parse_entry(raw_fields)
                    payload, retries = parse_payload(data)
                    logger.info(f"Received email job: msg_id={msg_id}, active={len(active_tasks)}")

                    task = asyncio.create_task(run_with_ack(
                        payload, False, retries, redis, WORKER_STREAM_EMAIL, msg_id, semaphore
                    ))
                    active_tasks.add(task)
                    task.add_done_callback(active_tasks.discard)

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
