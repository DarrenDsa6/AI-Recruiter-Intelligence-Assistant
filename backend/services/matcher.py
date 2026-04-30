import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from services.vector_store import VectorStoreService
from services.skills import SkillExtractionService
from services.semantic_matcher import SemanticMatcher
from services.jd_skill_classifier import JDSkillClassifier
from services.weighted_skill_gap_analyzer import WeightedSkillGapAnalyzer
from services.embedding_service import EmbedderService
from services.explainer import MatchExplainer


class MatcherService:

    def __init__(self, llm_service):
        print("Initializing Matcher Service...")

        # -----------------------------
        # Core services (deterministic layer)
        # -----------------------------
        self.vector_store = VectorStoreService()
        self.skill_extractor = SkillExtractionService()
        self.semantic_matcher = SemanticMatcher()
        self.jd_classifier = JDSkillClassifier()
        self.weighted_analyzer = WeightedSkillGapAnalyzer()
        self.embedding_service = EmbedderService()
        self.explainer = MatchExplainer()

        # -----------------------------
        # LLM layer (intelligence layer)
        # -----------------------------
        self.llm = llm_service

    # =====================================================
    # CORE MATCHING ENGINE (deterministic logic)
    # =====================================================
    def compute_similarity(self, job_description):

        stored_data = self.vector_store.get_all_documents()

        if not stored_data["documents"]:
            raise ValueError("No resume found in vector store.")

        resume_text = " ".join(stored_data["documents"])

        # -----------------------------
        # Resume skills
        # -----------------------------
        stored_metadata = stored_data.get("metadatas", [])

        if stored_metadata and "skills" in stored_metadata[0]:
            resume_skills = stored_metadata[0]["skills"]
        else:
            resume_skills = self.skill_extractor.extract_skills(resume_text)

        # -----------------------------
        # JD skills
        # -----------------------------
        jd_skills = self.skill_extractor.extract_skills(job_description)

        jd_classification = self.jd_classifier.classify_skills(
            job_description,
            jd_skills
        )

        required_skills = jd_classification["required"]
        optional_skills = jd_classification["optional"]

        # -----------------------------
        # Semantic matching
        # -----------------------------
        matched_skills = self.semantic_matcher.semantic_skill_match(
            resume_skills,
            jd_skills
        )

        # -----------------------------
        # Weighted analysis
        # -----------------------------
        weighted_result = self.weighted_analyzer.analyze(
            required_skills,
            optional_skills,
            matched_skills
        )

        # -----------------------------
        # Embedding similarity
        # -----------------------------
        jd_embedding = self.embedding_service.get_embeddings([job_description])[0]
        resume_embedding = self.embedding_service.get_embeddings([resume_text])[0]

        doc_score = float(
            cosine_similarity([jd_embedding], [resume_embedding])[0][0]
        )

        skill_score = weighted_result["match_score"] / 100

        final_score = (skill_score * 0.7) + (doc_score * 0.3)
        final_percent = round(final_score * 100, 2)

        # -----------------------------
        # Explanation layer
        # -----------------------------
        explanation = self.explainer.generate_explanation(
            matched_skills=matched_skills,
            missing_skills=weighted_result["missing_required"] + weighted_result["missing_optional"],
            match_score=final_percent
        )

        # -----------------------------
        # Final output
        # -----------------------------
        return {
            "required_skills": required_skills,
            "optional_skills": optional_skills,
            "matched_skills": matched_skills,
            "missing_required": weighted_result["missing_required"],
            "missing_optional": weighted_result["missing_optional"],
            "skill_score": weighted_result["match_score"],
            "document_score": round(doc_score * 100, 2),
            "final_score": final_percent,
            "summary": explanation["summary"],
            "recommendations": weighted_result["recommendations"]
        }

    # =====================================================
    # FULL AI PIPELINE (LLM + deterministic engine)
    # =====================================================
    def full_analysis(self, resume, jd, github_data):

    # ✅ extract text properly
        jd_text = jd["text"]

        # 1. deterministic match
        match_result = self.compute_similarity(jd_text)

        github_analysis = self.llm.analyze_github_repos(github_data)

        report = self.llm.generate_candidate_report(
            resume=resume["text"],
            jd=jd_text,
            match_result=match_result,
            github_context=github_analysis
        )

        questions = self.llm.generate_interview_questions(
            resume=resume["text"],
            jd=jd_text,
            missing_skills=match_result["missing_required"],
            github_context=github_analysis
        )

        return {
            "match": match_result,
            "github": github_analysis,
            "report": report,
            "questions": questions
        }