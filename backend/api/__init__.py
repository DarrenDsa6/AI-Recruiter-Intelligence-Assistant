from api.auth import router as auth_router
from api.upload import router as upload_router
from api.github import router as github_router
from api.match import router as match_router
from api.session import router as session_router
from api.chat import router as chat_router
from api.search import router as search_router

__all__ = [
    "auth_router",
    "upload_router",
    "github_router",
    "match_router",
    "session_router",
    "chat_router",
    "search_router",
]
