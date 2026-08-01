import json
import asyncio
import logging
import os
import platform
import re
import sys
import time
from datetime import datetime, timezone, timedelta

from sqlalchemy import and_, or_, select, update

sys.path.insert(0, os.path.dirname(__file__))

from config.constants import (
    WORKER_STREAM_URGENT,
    WORKER_STREAM_EMAIL,
    WORKER_MAX_RETRIES,
    STUCK_PENDING_MINUTES,
    STUCK_PROCESSING_MINUTES,
    STUCK_SCAN_INTERVAL_SECONDS,
    PENDING_RECOVERY_INTERVAL_SECONDS,
)
from services.database import init_db, close_db
import services.database as db_module
from services.redis import get_redis, close_redis
from services.matching import matcher
from services.llm import llm_client
from services.storage import vector_store
from services.guardrails.pii import scrub_pii, blind_screening_scrub
from services.agents import TechnicalAgent, HRAgent, MetaAgent
from services.pdf import generate_report_pdf
from services.integrations.brevo import brevo_email
from services.cleanup import purger
from models.report import TailoringReport
from models.user import User
from models.resume import MasterResume

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] [worker] %(name)s: %(message)s")
logger = logging.getLogger("worker")

CONSUMER_GROUP = "ai-recruiter"
CONSUMER_NAME = f"worker-{platform.node()}-{os.getpid()}"
CLEANUP_INTERVAL = 100
WORKER_CONCURRENCY = 3

technical_agent = TechnicalAgent()
hr_agent = HRAgent()
meta_agent = MetaAgent()


async def _load_github_context(db, resume_id) -> dict:
    result = await db.execute(
        select(MasterResume.github_data).where(MasterResume.id == resume_id)
    )
    github_data = result.scalar_one_or_none()
    if not github_data:
        return {}
    if isinstance(github_data, list):
        return {"repos": github_data}
    if isinstance(github_data, dict):
        return github_data if "repos" in github_data else {"repos": github_data}
    return {}


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
        logger.info(f"[{report_id}] Step 1/5: Computing similarity + hybrid search...")
        match_result = await matcher.compute_similarity(db, payload["jd_text"], payload["resume_id"], redis=redis)
        logger.info(f"[{report_id}] Step 1/5: Done | match_score={match_result.get('final_score')}%")

        resume_text = await vector_store.get_resume_text(db, payload["resume_id"])
        clean_resume = scrub_pii(resume_text)
        blind_resume = blind_screening_scrub(resume_text)

        logger.info(f"[{report_id}] Step 1b/5: Running LLM-based ATS evaluation...")
        try:
            ats_eval = await llm_client.evaluate_ats_match(clean_resume, payload["jd_text"], match_result)
            raw_score = ats_eval.get("ats_score")
            if isinstance(raw_score, (int, float)) and 0 <= float(raw_score) <= 100:
                llm_score = round(float(raw_score), 2)
                match_result["final_score"] = llm_score
                match_result["ats_score"] = llm_score
                match_result["ats_evaluation"] = ats_eval
                logger.info(f"[{report_id}] Step 1b/5: Done | llm_ats_score={llm_score}%")
            else:
                logger.warning(f"[{report_id}] Step 1b/5: LLM ATS score invalid ({raw_score!r}), keeping heuristic {match_result.get('final_score')}%")
        except Exception as e:
            logger.warning(f"[{report_id}] Step 1b/5: LLM ATS evaluation failed, keeping heuristic score: {e}")

        logger.info(f"[{report_id}] Step 2/5: Running agentic workflow (Technical + HR agents) concurrently...")
        github_context = payload.get("github_context", {})
        technical_result, hr_result = await asyncio.gather(
            technical_agent.analyze(github_context, llm_client),
            hr_agent.analyze(clean_resume, llm_client),
        )
        logger.info(f"[{report_id}] Step 2/5: Done | technical={technical_result.get('repo_count', 0)} repos | hr={hr_result.get('estimated_tenure_years', 0)}yrs")

        logger.info(f"[{report_id}] Step 2b/5: Meta-agent evaluating all signals...")
        meta_result = await meta_agent.evaluate(
            technical_result, hr_result, match_result, payload["jd_text"], llm_client
        )
        logger.info(f"[{report_id}] Step 2b/5: Done | meta_score={meta_result.get('final_score', '?')} | recommendation={meta_result.get('recommendation', '?')}")

        agent_analysis = {
            "technical": technical_result,
            "hr": hr_result,
            "meta": meta_result,
        }

        logger.info(f"[{report_id}] Step 3/5: Generating candidate report...")
        report = await llm_client.generate_candidate_report(clean_resume, payload["jd_text"], match_result, {})
        report["ats_score"] = match_result["final_score"]
        logger.info(f"[{report_id}] Step 3/5: Done | ats_score={report['ats_score']}")

        logger.info(f"[{report_id}] Step 4/5: Generating interview questions + prep + outreach concurrently...")
        questions, interview_prep, outreach_email = await asyncio.gather(
            llm_client.generate_interview_questions(
                clean_resume, payload["jd_text"], match_result.get("missing_required", []), {}
            ),
            llm_client.generate_interview_prep(
                clean_resume, payload["jd_text"], match_result, {}
            ),
            llm_client.generate_outreach_email(
                blind_resume, payload["jd_text"], match_result, {}
            ),
        )
        logger.info(f"[{report_id}] Step 4/5: Done | questions_count={sum(len(v) for v in questions.values() if isinstance(v, list))} | subject={outreach_email.get('subject', '?')[:60]}")

        logger.info(f"[{report_id}] Step 5/5: Generating actionable rewrites...")
        low_chunks = match_result.get("low_scoring_chunks", [])
        logger.info(f"[{report_id}] Step 5/5: low_scoring_chunks count={len(low_chunks)}")
        rewrites = await llm_client.generate_actionable_rewrites(
            low_chunks, payload["jd_text"]
        )
        logger.info(f"[{report_id}] Step 5/5: Done | rewrites_count={len(rewrites.get('rewrites', []))}")
        logger.info(f"[{report_id}] All LLM calls complete — saving to database")

        await db.execute(
            update(TailoringReport)
            .where(TailoringReport.id == report_id)
            .values(
                status="completed",
                match_result=match_result,
                report=report,
                questions=questions,
                rewrites=rewrites,
                agent_analysis=agent_analysis,
                github_analysis=technical_result,
                interview_prep=interview_prep,
                outreach_email=outreach_email,
                error_message=None,
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
                    pdf_bytes = await asyncio.to_thread(
                        generate_report_pdf,
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
                        report=report,
                        questions=questions,
                        rewrites=rewrites,
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


async def recover_pending(redis, stream_name, semaphore, active_tasks, active_report_ids, is_urgent):
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

            spawn_job(payload, is_urgent, retries, redis, stream_name, msg_id, semaphore, active_tasks, active_report_ids)
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


def spawn_job(payload, is_urgent, retries, redis, stream_name, msg_id, semaphore, active_tasks, active_report_ids):
    report_id = str(payload.get("report_id", ""))
    task = asyncio.create_task(
        run_with_ack(payload, is_urgent, retries, redis, stream_name, msg_id, semaphore)
    )
    active_tasks.add(task)
    task.add_done_callback(active_tasks.discard)
    if report_id:
        active_report_ids.add(report_id)
        task.add_done_callback(lambda t, rid=report_id: active_report_ids.discard(rid))
    return task


AUTO_REQUEUE_PREFIX = "auto-requeue"


def _stuck_recovery_attempts(error_message):
    if not error_message or AUTO_REQUEUE_PREFIX not in error_message:
        return 0
    match = re.search(rf"{AUTO_REQUEUE_PREFIX}\s*\((\d+)/", error_message)
    return int(match.group(1)) if match else 0


async def requeue_stuck_jobs(redis, active_report_ids):
    now = datetime.now(timezone.utc)
    async with db_module.async_session_factory() as db:
        result = await db.execute(
            select(TailoringReport).where(
                or_(
                    and_(
                        TailoringReport.status == "pending",
                        TailoringReport.created_at < now - timedelta(minutes=STUCK_PENDING_MINUTES),
                    ),
                    and_(
                        TailoringReport.status == "processing",
                        TailoringReport.created_at < now - timedelta(minutes=STUCK_PROCESSING_MINUTES),
                    ),
                )
            )
        )
        stuck = list(result.scalars().all())
        if not stuck:
            return {"requeued": 0, "failed": 0}

        logger.warning(f"Found {len(stuck)} stuck jobs to reconcile")
        requeued = failed = 0
        for report in stuck:
            if str(report.id) in active_report_ids:
                logger.debug(f"Skipping in-flight report={report.id}")
                continue

            attempts = _stuck_recovery_attempts(report.error_message) + 1
            if attempts > WORKER_MAX_RETRIES:
                report.status = "failed"
                report.error_message = "Job was stuck and exceeded automatic recovery attempts."
                report.completed_at = now
                failed += 1
                logger.error(f"Marked stuck report={report.id} as failed (recovery attempts={WORKER_MAX_RETRIES})")
                continue

            payload = json.dumps({
                "report_id": str(report.id),
                "user_id": str(report.user_id),
                "resume_id": str(report.resume_id),
                "jd_text": report.jd_text,
                "send_email": False,
                "github_context": await _load_github_context(db, report.resume_id),
            })
            await redis.xadd(WORKER_STREAM_URGENT, "*", {"payload": payload})
            report.status = "pending"
            report.error_message = f"{AUTO_REQUEUE_PREFIX} ({attempts}/{WORKER_MAX_RETRIES})"
            requeued += 1
            logger.warning(f"Requeued stuck report={report.id} (recovery attempt {attempts}/{WORKER_MAX_RETRIES})")
        await db.commit()
        return {"requeued": requeued, "failed": failed}


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
    active_report_ids: set[str] = set()

    logger.info(f"Checking for pending entries...")
    await recover_pending(redis, WORKER_STREAM_URGENT, semaphore, active_tasks, active_report_ids, is_urgent=True)
    await recover_pending(redis, WORKER_STREAM_EMAIL, semaphore, active_tasks, active_report_ids, is_urgent=False)

    logger.info(f"Listening on '{WORKER_STREAM_URGENT}' (priority) and '{WORKER_STREAM_EMAIL}' (email)")

    poll_count = 0
    last_pending_recovery = time.monotonic()
    last_stuck_scan = time.monotonic()
    while True:
        try:
            urgent_entries = await read_stream(redis, WORKER_STREAM_URGENT)
            if urgent_entries:
                for msg_id, raw_fields in urgent_entries:
                    data = parse_entry(raw_fields)
                    payload, retries = parse_payload(data)
                    logger.info(f"Received urgent job: msg_id={msg_id}, active={len(active_tasks)}")
                    spawn_job(payload, True, retries, redis, WORKER_STREAM_URGENT, msg_id, semaphore, active_tasks, active_report_ids)

            email_entries = await read_stream(redis, WORKER_STREAM_EMAIL)
            if email_entries:
                for msg_id, raw_fields in email_entries:
                    data = parse_entry(raw_fields)
                    payload, retries = parse_payload(data)
                    logger.info(f"Received email job: msg_id={msg_id}, active={len(active_tasks)}")
                    spawn_job(payload, False, retries, redis, WORKER_STREAM_EMAIL, msg_id, semaphore, active_tasks, active_report_ids)

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

            if time.monotonic() - last_pending_recovery >= PENDING_RECOVERY_INTERVAL_SECONDS:
                last_pending_recovery = time.monotonic()
                await recover_pending(redis, WORKER_STREAM_URGENT, semaphore, active_tasks, active_report_ids, is_urgent=True)
                await recover_pending(redis, WORKER_STREAM_EMAIL, semaphore, active_tasks, active_report_ids, is_urgent=False)

            if time.monotonic() - last_stuck_scan >= STUCK_SCAN_INTERVAL_SECONDS:
                last_stuck_scan = time.monotonic()
                try:
                    result = await requeue_stuck_jobs(redis, active_report_ids)
                    if any(v > 0 for v in result.values()):
                        logger.warning(f"Stuck-job reconciliation: {result}")
                except Exception as reconcile_err:
                    logger.error(f"Stuck-job reconciliation failed: {reconcile_err}")

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
