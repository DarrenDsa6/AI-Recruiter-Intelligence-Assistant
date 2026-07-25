import logging

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from services.storage.vector_store import vector_store
from services.parsing.skills import SkillExtractionService
from services.matching.semantic_matcher import SemanticMatcher
from services.matching.skill_classifier import JDSkillClassifier
from services.matching.skill_gap_analyzer import WeightedSkillGapAnalyzer
from services.matching.explainer import MatchExplainer
from services.embedding.embedder import embedder

logger = logging.getLogger(__name__)


class MatcherService:
    def __init__(self):
        self.vector_store = vector_store
        self.skill_extractor = SkillExtractionService()
        self.semantic_matcher = SemanticMatcher()
        self.jd_classifier = JDSkillClassifier()
        self.weighted_analyzer = WeightedSkillGapAnalyzer()
        self.embedding_service = embedder
        self.explainer = MatchExplainer()

    async def compute_similarity(self, db, job_description: str, resume_id) -> dict:
        stored_data = await self.vector_store.get_by_resume(db, resume_id)

        vecs = stored_data.get("embeddings")
        documents = stored_data.get("documents", [])
        metadatas = stored_data.get("metadatas", [])

        if not vecs:
            raise ValueError("No embeddings found for resume")

        resume_text = " ".join(documents)
        resume_embedding = self._aggregate_embeddings(vecs)

        if metadatas and "skills" in metadatas[0]:
            resume_skills = metadatas[0]["skills"]
        else:
            resume_skills = self.skill_extractor.extract_skills(resume_text)

        jd_skills = self.skill_extractor.extract_skills(job_description)
        jd_classification = self.jd_classifier.classify_skills(job_description, jd_skills)

        required_skills = jd_classification["required"]
        optional_skills = jd_classification["optional"]

        matched_skills = self.semantic_matcher.semantic_skill_match(resume_skills, jd_skills)

        weighted_result = self.weighted_analyzer.analyze(required_skills, optional_skills, matched_skills)

        jd_embedding = self.embedding_service.get_embeddings([job_description])[0]
        doc_score = float(cosine_similarity([jd_embedding], [resume_embedding])[0][0])

        skill_score = weighted_result["match_score"] / 100
        final_score = (skill_score * 0.7) + (doc_score * 0.3)
        final_percent = round(final_score * 100, 2)

        explanation = self.explainer.generate_explanation(
            matched_skills=matched_skills,
            missing_skills=weighted_result["missing_required"] + weighted_result["missing_optional"],
            match_score=final_percent,
        )

        chunk_scores = self._score_chunks(documents, job_description)

        return {
            "required_skills": required_skills,
            "optional_skills": optional_skills,
            "matched_skills": matched_skills,
            "missing_required": weighted_result["missing_required"],
            "missing_optional": weighted_result["missing_optional"],
            "skill_score": weighted_result["match_score"],
            "document_score": round(doc_score * 100, 2),
            "final_score": final_percent,
            "ats_score": final_percent,
            "summary": explanation["summary"],
            "recommendations": weighted_result["recommendations"],
            "low_scoring_chunks": chunk_scores[:3],
        }

    def _score_chunks(self, documents: list[str], job_description: str, top_n: int = 3) -> list[dict]:
        if not documents:
            return []
        jd_embedding = self.embedding_service.get_embeddings([job_description])[0]
        chunk_embeddings = self.embedding_service.get_embeddings(documents)
        scores = [
            {"chunk_index": i, "text": doc[:200], "score": round(float(cosine_similarity([jd_embedding], [emb])[0][0]), 4)}
            for i, (doc, emb) in enumerate(zip(documents, chunk_embeddings))
        ]
        scores.sort(key=lambda x: x["score"])
        return scores[:top_n]

    def _aggregate_embeddings(self, embeddings) -> np.ndarray:
        return np.mean(embeddings, axis=0)


matcher = MatcherService()
