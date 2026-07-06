from fastapi import APIRouter

from services.provider_config import PROVIDER_CONFIGS

router = APIRouter()


@router.get("/models")
async def list_models():
    return PROVIDER_CONFIGS
