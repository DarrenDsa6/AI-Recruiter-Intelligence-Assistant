import os
import logging
from datetime import datetime, timezone
from sqlalchemy import Text, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
import uuid

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_login: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MasterResume(Base):
    __tablename__ = "master_resumes"
    __table_args__ = (
        UniqueConstraint("user_id", "file_hash", name="uq_user_file_hash"),
    )

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    file_hash: Mapped[str] = mapped_column(Text, nullable=False)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    chroma_resume_id: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class TailoringReport(Base):
    __tablename__ = "tailoring_reports"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("master_resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    jd_text: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, default="pending")  # pending | processing | completed | failed
    match_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    github_analysis: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    questions: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    rewrites: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


engine = None
async_session_factory = None


async def init_db():
    global engine, async_session_factory
    db_url = os.environ.get("DATABASE_CONNECTION_STRING")
    if not db_url:
        raise RuntimeError("DATABASE_CONNECTION_STRING must be set")
    engine = create_async_engine(db_url, echo=False, pool_size=5, max_overflow=10)
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized")


async def close_db():
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connection pool closed")


async def get_db() -> AsyncSession:
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with async_session_factory() as session:
        yield session
