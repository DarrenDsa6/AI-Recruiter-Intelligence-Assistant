from fastapi import FastAPI
from api.upload import router as upload_router
from api.search import router as search_router
from api.github import router as github_router

app = FastAPI(
    title="AI Recruiter Intelligence Assistant"
)

app.include_router(
    upload_router,
    prefix="/api"
)

app.include_router(
    search_router,
    prefix="/api"
)

app.include_router(
    github_router,
    prefix="/api"
)

@app.get("/")
def root():
    return {"message": "AI Recruiter Backend Running"}