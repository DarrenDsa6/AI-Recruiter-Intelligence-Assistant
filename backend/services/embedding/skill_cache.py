import logging
import os

import numpy as np

from config.constants import SEMANTIC_MATCH_MODEL
from services.embedding.model_registry import ModelRegistry

logger = logging.getLogger(__name__)

CACHE_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "data", "skill_embeddings.pkl")


class SkillEmbeddingCache:
    def __init__(self):
        self.model = ModelRegistry.get(SEMANTIC_MATCH_MODEL)
        self.embeddings: dict[str, object] = {}
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(CACHE_PATH):
            try:
                self.embeddings = np.load(CACHE_PATH, allow_pickle=True).item()
                logger.info(f"Loaded {len(self.embeddings)} cached skill embeddings")
            except Exception as e:
                logger.warning(f"Failed to load skill cache, starting fresh: {e}")
                self.embeddings = {}
        else:
            logger.info("No existing skill embedding cache found")

    def save_cache(self):
        np.save(CACHE_PATH, self.embeddings)
        logger.info(f"Saved {len(self.embeddings)} skill embeddings")

    def build_cache(self, skills: list[str]):
        new_skills = [s for s in skills if s not in self.embeddings]
        if not new_skills:
            logger.info("All skills already cached")
            return
        logger.info(f"Embedding {len(new_skills)} new skills")
        vectors = self.model.encode(new_skills, normalize_embeddings=True)
        for skill, vec in zip(new_skills, vectors):
            self.embeddings[skill] = vec
        self.save_cache()

    def get_embedding(self, skill: str):
        return self.embeddings.get(skill)
