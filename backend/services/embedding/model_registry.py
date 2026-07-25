import logging

from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


class ModelRegistry:
    _instances: dict[str, SentenceTransformer] = {}

    @classmethod
    def get(cls, model_name: str) -> SentenceTransformer:
        if model_name not in cls._instances:
            logger.info(f"Loading model: {model_name}")
            cls._instances[model_name] = SentenceTransformer(model_name)
        return cls._instances[model_name]
