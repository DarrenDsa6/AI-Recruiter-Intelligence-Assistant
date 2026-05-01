from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio

from api.upload import router as upload_router
from api.github import router as github_router
from api.match import router as match_router
from api.session import router as session_router

from services.session_store import session_store
from services.vector_store import VectorStoreService

vector_store = VectorStoreService()

async def cleanup_sessions():
    while True:
        try:
            expired_sessions = session_store.get_expired_sessions()

            for session_id in expired_sessions:
                print(f"Cleaning session: {session_id}")

                deleted = vector_store.delete_by_session(session_id)

                print(f"Deleted {deleted} chunks")

                session_store.delete_session(session_id)

        except Exception as e:
            print("Cleanup error:", str(e))

        await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting cleanup worker...")

    task = asyncio.create_task(cleanup_sessions())

    yield

    print("Stopping cleanup worker...")

    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        print("Cleanup worker stopped")


app = FastAPI(
    title="AI Recruiter Intelligence Assistant",
    lifespan=lifespan
)

# routers
app.include_router(upload_router, prefix="/api")
app.include_router(github_router, prefix="/api")
app.include_router(match_router, prefix="/api")
app.include_router(session_router, prefix="/api")


@app.get("/")
def root():
    return {"message": "AI Recruiter Backend Running"}

@app.get("/routes")
def get_routes():
    return [route.path for route in app.routes]