import pickle
import logging
import os

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
            with open(CACHE_PATH, "rb") as f:
                self.embeddings = pickle.load(f)
            logger.info(f"Loaded {len(self.embeddings)} cached skill embeddings")
        else:
            logger.info("No existing skill embedding cache found")

    def save_cache(self):
        with open(CACHE_PATH, "wb") as f:
            pickle.dump(self.embeddings, f)
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
