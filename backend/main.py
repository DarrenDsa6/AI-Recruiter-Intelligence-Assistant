from fastapi import FastAPI
from api.upload import router as upload_router

app = FastAPI(
    title="AI Recruiter Intelligence Assistant",
    version="1.0.0"
)

app.include_router(
    upload_router,
    prefix="/api"
)


@app.get("/")
def root():
    return {
        "message": "AI Recruiter Backend Running 🚀"
    }