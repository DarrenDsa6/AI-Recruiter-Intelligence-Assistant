import logging

import numpy as np

from config.constants import SEMANTIC_MATCH_MODEL
from services.embedding.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class SkillEmbeddingCache:
    def __init__(self):
        self.model = ModelRegistry.get(SEMANTIC_MATCH_MODEL)
        self.embeddings: dict[str, object] = {}

    def build_cache(self, skills: list[str]):
        new_skills = [s for s in skills if s not in self.embeddings]
        if not new_skills:
            logger.info("All skills already cached")
            return
        logger.info(f"Embedding {len(new_skills)} new skills")
        vectors = self.model.encode(new_skills, normalize_embeddings=True)
        for skill, vec in zip(new_skills, vectors):
            self.embeddings[skill] = vec

    def get_embedding(self, skill: str):
        return self.embeddings.get(skill)
