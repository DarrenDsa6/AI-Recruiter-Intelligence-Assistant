import logging
from datetime import datetime, timezone, timedelta

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.chunk import ResumeChunk
from models.report import TailoringReport
from models.resume import MasterResume
from models.user import User
from config.constants import CHUNK_RETENTION_DAYS, REPORT_RETENTION_DAYS

logger = logging.getLogger(__name__)


class DataPurger:
    async def purge_old_chunks(self, db: AsyncSession) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=CHUNK_RETENTION_DAYS)
        referenced_resumes = select(TailoringReport.resume_id).distinct().scalar_subquery()
        result = await db.execute(
            delete(ResumeChunk).where(
                ResumeChunk.created_at < cutoff,
                ResumeChunk.resume_id.notin_(referenced_resumes),
            )
        )
        await db.commit()
        if result.rowcount:
            logger.info(f"Purged {result.rowcount} chunks older than {CHUNK_RETENTION_DAYS}d (unreferenced resumes only)")
        return result.rowcount

    async def purge_old_reports(self, db: AsyncSession) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=REPORT_RETENTION_DAYS)
        result = await db.execute(
            delete(TailoringReport).where(
                and_(
                    TailoringReport.created_at < cutoff,
                    TailoringReport.status.in_(["completed", "failed"]),
                )
            )
        )
        await db.commit()
        if result.rowcount:
            logger.info(f"Purged {result.rowcount} reports older than {REPORT_RETENTION_DAYS}d")
        return result.rowcount

    async def purge_orphaned_resumes(self, db: AsyncSession) -> int:
        from sqlalchemy import select, not_

        result_subq = select(TailoringReport.resume_id).distinct().scalar_subquery()
        chunk_subq = select(ResumeChunk.resume_id).distinct().scalar_subquery()

        result = await db.execute(
            delete(MasterResume).where(
                and_(
                    ~MasterResume.id.in_(result_subq),
                    ~MasterResume.id.in_(chunk_subq),
                )
            )
        )
        await db.commit()
        if result.rowcount:
            logger.info(f"Purged {result.rowcount} orphaned resumes")
        return result.rowcount

    async def purge_anonymous_users(self, db: AsyncSession) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=30)
        result = await db.execute(
            delete(User).where(
                and_(
                    User.email.like("anon-%"),
                    User.last_login.is_(None),
                    User.created_at < cutoff,
                )
            )
        )
        await db.commit()
        if result.rowcount:
            logger.info(f"Purged {result.rowcount} anonymous users older than 30d")
        return result.rowcount

    async def run_cleanup(self, db: AsyncSession) -> dict:
        chunks = await self.purge_old_chunks(db)
        reports = await self.purge_old_reports(db)
        orphans = await self.purge_orphaned_resumes(db)
        anons = await self.purge_anonymous_users(db)
        return {"chunks_purged": chunks, "reports_purged": reports, "orphans_purged": orphans, "anonymous_users_purged": anons}


purger = DataPurger()
