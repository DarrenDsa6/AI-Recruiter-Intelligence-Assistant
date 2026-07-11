from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import os
import logging
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from api.auth import router as auth_router
from api.upload import router as upload_router
from api.github import router as github_router
from api.match import router as match_router
from api.session import router as session_router
from api.chat import router as chat_router

from services.db import init_db, close_db
from services.redis_client import close_redis
from services.model_registry import ModelRegistry, DOC_EMBEDDING_MODEL

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    await init_db()

    logger.info("Pre-warming embedding model...")
    await asyncio.to_thread(ModelRegistry.get, DOC_EMBEDDING_MODEL)
    logger.info("Embedding model loaded")

    yield

    # Shutdown
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

# Prometheus metrics
Instrumentator().instrument(app).expose(app)

# Routers
app.include_router(auth_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(github_router, prefix="/api")
app.include_router(match_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(chat_router, prefix="/api")

# CORS
_cors_origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]
_env_origins = os.environ.get("CORS_ORIGINS", "")
if _env_origins:
    _cors_origins.extend([o.strip() for o in _env_origins.split(",") if o.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "service": "AI Resume Tailor",
        "status": "running",
        "version": "2.0.0",
    }


@app.get("/api/health")
async def health():
    checks = {"status": "ok"}

    # Check DB
    try:
        from services.db import engine
        if engine:
            async with engine.connect() as conn:
                await conn.execute(
                    __import__("sqlalchemy").text("SELECT 1")
                )
            checks["database"] = "ok"
        else:
            checks["database"] = "not initialized"
    except Exception as e:
        checks["database"] = f"error: {str(e)}"

    # Check Redis
    try:
        from services.redis_client import get_redis
        redis = await get_redis()
        await redis.ping()
        checks["redis"] = "ok"
    except Exception as e:
        checks["redis"] = f"error: {str(e)}"

    if any("error" in v for v in checks.values()):
        checks["status"] = "degraded"

    return checks
