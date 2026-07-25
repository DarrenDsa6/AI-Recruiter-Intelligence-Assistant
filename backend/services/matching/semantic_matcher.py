import logging

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from services.embedding.embedder import embedder
from services.embedding.skill_cache import SkillEmbeddingCache
from services.embedding.model_registry import ModelRegistry
from config.constants import SEMANTIC_MATCH_MODEL

logger = logging.getLogger(__name__)


class SemanticMatcher:
    def __init__(self):
        self.model = ModelRegistry.get(SEMANTIC_MATCH_MODEL)
        self.cache = SkillEmbeddingCache()
        logger.info(f"Loaded {len(self.cache.embeddings)} cached skill embeddings")

    def get_cached_embeddings(self, skills: list[str]) -> np.ndarray:
        skills = [s.lower().strip() for s in skills]
        vectors = [None] * len(skills)
        missing_skills = []
        missing_indices = []

        for idx, skill in enumerate(skills):
            vec = self.cache.get_embedding(skill)
            if vec is not None:
                vectors[idx] = vec
            else:
                missing_skills.append(skill)
                missing_indices.append(idx)

        if missing_skills:
            logger.info(f"Embedding {len(missing_skills)} uncached skills")
            new_vectors = self.model.encode(missing_skills, normalize_embeddings=True)
            for idx, skill, vec in zip(missing_indices, missing_skills, new_vectors):
                self.cache.embeddings[skill] = vec
                vectors[idx] = vec
            self.cache.save_cache()

        return np.array(vectors)

    def semantic_skill_match(
        self, resume_skills: list[str], jd_skills: list[str], threshold: float = 0.80
    ) -> list[str]:
        if not resume_skills or not jd_skills:
            return []

        resume_skills = [s.lower().strip() for s in resume_skills]
        jd_skills = [s.lower().strip() for s in jd_skills]

        resume_vecs = self.get_cached_embeddings(resume_skills)
        jd_vecs = self.get_cached_embeddings(jd_skills)

        similarity_matrix = np.dot(resume_vecs, jd_vecs.T)

        matches: set[str] = set()
        for i in range(len(resume_skills)):
            for j in range(len(jd_skills)):
                if similarity_matrix[i][j] >= threshold:
                    logger.debug(f"Match: {resume_skills[i]} ~= {jd_skills[j]} ({similarity_matrix[i][j]:.3f})")
                    matches.add(jd_skills[j])

        return list(matches)
