from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import logging
from fastapi.middleware.cors import CORSMiddleware

from api.upload import router as upload_router
from api.github import router as github_router
from api.match import router as match_router
from api.session import router as session_router
from api.chat import router as chat_router

from services.session_store import session_store
from services.vector_store import vector_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def cleanup_sessions():
    while True:
        try:
            expired = session_store.get_expired_sessions()

            for session_id in expired:
                logger.info(f"Cleaning expired session: {session_id}")
                deleted = vector_store.delete_by_session(session_id)
                logger.info(f"Deleted {deleted} chunks")
                session_store.delete_session(session_id)

        except Exception as e:
            logger.error(f"Cleanup error: {e}")

        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting cleanup worker...")
    task = asyncio.create_task(cleanup_sessions())

    yield

    logger.info("Stopping cleanup worker...")
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        logger.info("Cleanup worker stopped")


app = FastAPI(
    title="AI Recruiter Intelligence Assistant",
    lifespan=lifespan
)

app.include_router(upload_router, prefix="/api")
app.include_router(github_router, prefix="/api")
app.include_router(match_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(chat_router, prefix="/api")


@app.get("/")
def root():
    return {
        "service": "AI Recruiter Backend",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
