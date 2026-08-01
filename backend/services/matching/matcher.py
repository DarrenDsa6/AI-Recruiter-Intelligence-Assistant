import asyncio
import hashlib
import json
import logging

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sqlalchemy import select

from services.storage.vector_store import vector_store
from services.parsing.skills import SkillExtractionService
from services.parsing import ChunkerService
from services.matching.semantic_matcher import SemanticMatcher
from services.matching.skill_classifier import JDSkillClassifier
from services.matching.skill_gap_analyzer import WeightedSkillGapAnalyzer
from services.matching.explainer import MatchExplainer
from services.matching.reranker import reranker
from services.embedding.embedder import embedder
from config.constants import JD_EMBEDDING_CACHE_TTL
from models.resume import MasterResume

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
        self.reranker = reranker
        self.chunker = ChunkerService()

    async def _get_or_cache_jd_embedding(self, redis, job_description: str) -> np.ndarray:
        jd_hash = hashlib.sha256(job_description.encode()).hexdigest()
        cache_key = f"jd_emb:{jd_hash}"

        cached = await redis.get(cache_key)
        if cached:
            logger.debug(f"JD embedding cache hit: {cache_key}")
            return np.array(json.loads(cached))

        embedding = (await asyncio.to_thread(self.embedding_service.get_embeddings, [job_description]))[0]
        await redis.setex(cache_key, JD_EMBEDDING_CACHE_TTL, json.dumps(embedding))
        logger.debug(f"JD embedding cached: {cache_key}")
        return np.array(embedding)

    async def _rebuild_chunks_from_raw_text(self, db, resume_id) -> bool:
        result = await db.execute(
            select(MasterResume.raw_text).where(MasterResume.id == resume_id)
        )
        raw_text = result.scalar_one_or_none()
        if not raw_text:
            return False
        try:
            chunk_dicts = self.chunker.chunk_semantic(raw_text)
            if not chunk_dicts:
                chunk_dicts = self.chunker.chunk_text(raw_text)
            if not chunk_dicts:
                return False

            chunk_texts = [c["text"] for c in chunk_dicts]
            chunk_sections = [c.get("section", "general") for c in chunk_dicts]
            embeddings = await asyncio.to_thread(self.embedding_service.get_embeddings, chunk_texts)
            if not embeddings:
                return False

            resume_skills = self.skill_extractor.extract_skills(raw_text)
            metadatas = [
                {"source": "resume", "skills": ", ".join(resume_skills), "section": sec}
                for sec in chunk_sections
            ]
            await self.vector_store.add_documents(
                db=db,
                documents=chunk_texts,
                embeddings=embeddings,
                metadatas=metadatas,
                resume_id=resume_id,
            )
            await db.commit()
            logger.warning(f"Rebuilt {len(chunk_texts)} resume chunks from raw_text (resume={resume_id})")
            return True
        except Exception as e:
            logger.error(f"Failed to rebuild chunks from raw_text (resume={resume_id}): {e}")
            await db.rollback()
            return False

    async def compute_similarity(self, db, job_description: str, resume_id, redis=None) -> dict:
        stored_data = await self.vector_store.get_by_resume(db, resume_id)

        vecs = stored_data.get("embeddings")
        documents = stored_data.get("documents", [])
        metadatas = stored_data.get("metadatas", [])

        if not vecs:
            rebuilt = await self._rebuild_chunks_from_raw_text(db, resume_id)
            if rebuilt:
                stored_data = await self.vector_store.get_by_resume(db, resume_id)
                vecs = stored_data.get("embeddings")
                documents = stored_data.get("documents", [])
                metadatas = stored_data.get("metadatas", [])

        if not vecs:
            raise ValueError("No embeddings found for resume")

        resume_text = " ".join(documents)
        resume_embedding = self._aggregate_embeddings(vecs)

        resume_skills = metadatas[0].get("skills", "") if metadatas else ""
        if not resume_skills:
            resume_skills = self.skill_extractor.extract_skills(resume_text)
        else:
            resume_skills = [s.strip() for s in resume_skills.split(",") if s.strip()]

        jd_skills = self.skill_extractor.extract_skills(job_description)
        jd_classification = self.jd_classifier.classify_skills(job_description, jd_skills)

        required_skills = jd_classification["required"]
        optional_skills = jd_classification["optional"]

        matched_skills = self.semantic_matcher.semantic_skill_match(resume_skills, jd_skills)

        weighted_result = self.weighted_analyzer.analyze(required_skills, optional_skills, matched_skills)

        if redis:
            jd_embedding = await self._get_or_cache_jd_embedding(redis, job_description)
        else:
            jd_embedding = (await asyncio.to_thread(self.embedding_service.get_embeddings, [job_description]))[0]

        doc_score = float(cosine_similarity([jd_embedding], [resume_embedding])[0][0])

        skill_score = weighted_result["match_score"] / 100
        final_score = (skill_score * 0.7) + (doc_score * 0.3)
        final_percent = round(final_score * 100, 2)

        explanation = self.explainer.generate_explanation(
            matched_skills=matched_skills,
            missing_skills=weighted_result["missing_required"] + weighted_result["missing_optional"],
            match_score=final_percent,
        )

        chunk_scores = await self._score_chunks(documents, job_description)

        category_breakdown = self._compute_category_breakdown(
            required_skills=required_skills,
            optional_skills=optional_skills,
            matched_skills=matched_skills,
            resume_skills=resume_skills,
            jd_skills=jd_skills,
            doc_score=doc_score,
            resume_text=resume_text,
        )

        reranked = self.reranker.rerank(job_description, documents, top_k=5)

        pros_cons = self.explainer.generate_pros_cons(
            matched_skills=matched_skills,
            missing_skills=weighted_result["missing_required"] + weighted_result["missing_optional"],
            resume_text=resume_text,
            jd_text=job_description,
            matched_chunks=reranked,
        )

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
            "category_breakdown": category_breakdown,
            "pros_cons": pros_cons,
            "reranked_chunks": reranked,
        }

    def _compute_category_breakdown(
        self,
        required_skills: list,
        optional_skills: list,
        matched_skills: list,
        resume_skills: list,
        jd_skills: list,
        doc_score: float,
        resume_text: str = "",
    ) -> dict:
        matched_set = set(s.lower() for s in matched_skills) if matched_skills else set()
        resume_set = set(s.lower() for s in resume_skills) if resume_skills else set()
        jd_set = set(s.lower() for s in jd_skills) if jd_skills else set()

        if required_skills:
            matched_required = sum(1 for s in required_skills if s.lower() in matched_set)
            skill_match_pct = round((matched_required / len(required_skills)) * 100, 1)
        else:
            skill_match_pct = round(doc_score * 100, 1)

        if optional_skills:
            matched_optional = sum(1 for s in optional_skills if s.lower() in matched_set)
            optional_pct = round((matched_optional / len(optional_skills)) * 100, 1)
        else:
            optional_pct = skill_match_pct

        experience_indicators = ["experience", "years", "senior", "lead", "managed", "developed", "implemented", "designed", "built", "achieved"]
        resume_exp_count = sum(1 for ind in experience_indicators if ind in resume_text.lower()) if resume_text else 0
        experience_score = min(100, round(resume_exp_count * 12.5))

        education_indicators = ["degree", "university", "college", "bachelor", "master", "phd", "gpa", "graduated"]
        has_education = any(ind in resume_text.lower() for ind in education_indicators) if resume_text else False
        education_score = 95 if has_education else 50

        project_indicators = ["project", "portfolio", "github", "contributed", "open source", "built", "launched"]
        resume_proj_count = sum(1 for ind in project_indicators if ind in resume_text.lower()) if resume_text else 0
        projects_score = min(100, round(resume_proj_count * 20))

        if jd_set:
            keyword_overlap = len(resume_set & jd_set)
            keyword_score = min(100, round((keyword_overlap / len(jd_set)) * 100, 1))
        else:
            keyword_score = round(doc_score * 100, 1)

        return {
            "skills": skill_match_pct,
            "experience": experience_score,
            "education": education_score,
            "projects": projects_score,
            "keywords": keyword_score,
            "overall": round(
                (skill_match_pct * 0.35)
                + (experience_score * 0.20)
                + (education_score * 0.10)
                + (projects_score * 0.15)
                + (keyword_score * 0.20),
                1,
            ),
        }

    async def _score_chunks(self, documents: list[str], job_description: str, top_n: int = 3) -> list[dict]:
        if not documents:
            logger.warning("[Matcher] _score_chunks: no documents to score")
            return []
        logger.info(f"[Matcher] _score_chunks: scoring {len(documents)} chunks against JD")
        jd_embedding = (await asyncio.to_thread(self.embedding_service.get_embeddings, [job_description]))[0]
        chunk_embeddings = await asyncio.to_thread(self.embedding_service.get_embeddings, documents)
        scores = [
            {"chunk_index": i, "text": doc[:200], "score": round(float(cosine_similarity([jd_embedding], [emb])[0][0]), 4)}
            for i, (doc, emb) in enumerate(zip(documents, chunk_embeddings))
        ]
        scores.sort(key=lambda x: x["score"])
        result = scores[:top_n]
        logger.info(f"[Matcher] _score_chunks: top {len(result)} lowest scores: {[s['score'] for s in result]}")
        return result

    def _aggregate_embeddings(self, embeddings) -> np.ndarray:
        return np.mean(embeddings, axis=0)


matcher = MatcherService()
