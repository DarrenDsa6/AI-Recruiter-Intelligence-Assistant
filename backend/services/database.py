import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from config.settings import settings
from config.constants import DB_POOL_SIZE, DB_MAX_OVERFLOW

logger = logging.getLogger(__name__)

engine = None
async_session_factory = None


async def init_db():
    global engine, async_session_factory

    db_url = settings.database_url_async
    if not db_url:
        raise RuntimeError("DATABASE_CONNECTION_STRING not set")

    engine = create_async_engine(
        db_url,
        echo=False,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
    )
    async_session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))

    logger.info("Database connected (pgvector ensured)")


async def close_db():
    global engine
    if engine:
        await engine.dispose()
        engine = None
    logger.info("Database connection pool closed")


async def get_db():
    if async_session_factory is None:
        raise RuntimeError("Database not initialized. Call init_db() first.")
    async with async_session_factory() as session:
        yield session
