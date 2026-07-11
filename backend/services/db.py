import os
import logging
from collections.abc import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy import text

logger = logging.getLogger(__name__)

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
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        import models.user  # noqa: F401
        import models.resume  # noqa: F401
        import models.chunk  # noqa: F401
        import models.report  # noqa: F401
        from models.user import Base
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialized (pgvector enabled)")


async def close_db():
    global engine
    if engine:
        await engine.dispose()
        logger.info("Database connection pool closed")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with async_session_factory() as session:
        yield session
