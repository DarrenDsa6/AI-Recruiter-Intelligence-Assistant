from fastapi import APIRouter
from pydantic import BaseModel

from services.vector_store import VectorStoreService

router = APIRouter()
vector_store = VectorStoreService()

class DeleteRequest(BaseModel):
    resume_id: str

@router.post("/delete")
async def delete_resume(request: DeleteRequest):
    deleted_count = (
        vector_store.delete_resume(
            request.resume_id
        )
    )
    return {
        "message":
            "Resume deleted successfully",
        "deleted_records":
            deleted_count
    }