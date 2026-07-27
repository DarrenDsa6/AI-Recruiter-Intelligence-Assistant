import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from prometheus_fastapi_instrumentator import Instrumentator

from config.settings import settings
from services.database import init_db, close_db
from services.redis import close_redis
from services.embedding import ModelRegistry
from config.constants import DOC_EMBEDDING_MODEL
from api import (
    auth_router,
    upload_router,
    github_router,
    match_router,
    session_router,
    chat_router,
    search_router,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)


class HealthCheckFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        if "GET /api/health" in msg:
            return False
        if "GET /" in msg and "200" in msg and record.name == "uvicorn.access":
            return False
        return True


logging.getLogger("uvicorn.access").addFilter(HealthCheckFilter())


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database...")
    await init_db()

    logger.info("Pre-warming embedding model...")
    await asyncio.to_thread(ModelRegistry.get, DOC_EMBEDDING_MODEL)
    logger.info("Embedding model loaded")

    yield

    logger.info("Shutting down...")
    await close_db()
    await close_redis()
    logger.info("Shutdown complete")


app = FastAPI(
    title="AI Resume Tailor",
    description="AI-powered resume analysis and optimization for candidates",
    version="2.0.0",
    lifespan=lifespan,
)

async def _verify_metrics_key(
    key: str = Security(APIKeyHeader(name="X-API-Key", auto_error=False)),
):
    if not settings.metrics_api_key:
        return
    if key != settings.metrics_api_key:
        raise HTTPException(status_code=403, detail="Invalid API key")


Instrumentator().instrument(app).expose(app, dependencies=[Depends(_verify_metrics_key)])

app.include_router(auth_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(github_router, prefix="/api")
app.include_router(match_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(chat_router, prefix="/api")
app.include_router(search_router, prefix="/api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-GitHub-Token", "X-API-Key"],
)


@app.get("/")
def root():
    return {"service": "AI Resume Tailor", "status": "running", "version": "2.0.0"}


@app.get("/api/health")
async def health():
    import time
    now = time.time()
    cached = getattr(app.state, "_health_cache", None)
    if cached and now - cached["ts"] < 30:
        return cached["result"]

    checks = {"status": "ok"}

    try:
        from services.database import engine
        if engine:
            from sqlalchemy import text
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            checks["database"] = "ok"
        else:
            checks["database"] = "not initialized"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    try:
        from services.redis import get_redis
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    if any("error" in v for v in checks.values()):
        checks["status"] = "degraded"

    app.state._health_cache = {"result": checks, "ts": now}
    return checks
