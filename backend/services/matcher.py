import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from services.vector_store import VectorStoreService
from services.skills import SkillExtractionService
from services.semantic_matcher import SemanticMatcher
from services.jd_skill_classifier import JDSkillClassifier
from services.weighted_skill_gap_analyzer import (
    WeightedSkillGapAnalyzer
)
from services.embedding_service import EmbedderService
from services.explainer import MatchExplainer


class MatcherService:
    def __init__(self):
        print("Initializing Matcher Service...")
        self.vector_store = VectorStoreService()
        self.skill_extractor = SkillExtractionService()
        self.semantic_matcher = SemanticMatcher()
        self.jd_classifier = JDSkillClassifier()
        self.weighted_analyzer = (
            WeightedSkillGapAnalyzer()
        )
        self.embedding_service = (
            EmbedderService()
        )
        self.explainer = MatchExplainer()

    def compute_similarity(self, job_description):
        print(
            "\n--- Starting Similarity Computation ---"
        )
        # STEP 0 — Load Resume from Vector Store
        stored_data = (
            self.vector_store
            .get_all_documents()
        )

        if not stored_data["documents"]:
            raise ValueError(
                "No resume found in vector store. Upload resume first."
            )

        resume_chunks = (
            stored_data["documents"]
        )

        resume_text = " ".join(
            resume_chunks
        )

        print(
            "Loaded resume length:",
            len(resume_text)
        )

        # STEP 0.1 — Load Resume Skills from Metadata
        stored_metadata = (
            stored_data.get("metadatas", [])
        )

        if stored_metadata:
            resume_skills = (
                stored_metadata[0]
                .get("skills", [])
            )
        else:
            # fallback if metadata missing
            resume_skills = (
                self.skill_extractor
                .extract_skills(
                    resume_text
                )
            )
        print(
            "Resume Skills:",
            resume_skills
        )

        # STEP 1 — Extract JD Skills
        jd_skills = (
            self.skill_extractor
            .extract_skills(
                job_description
            )
        )

        print(
            "JD Skills:",
            jd_skills
        )

        # STEP 2 — Classify JD Skills
        jd_classification = (
            self.jd_classifier
            .classify_skills(
                job_description,
                jd_skills
            )
        )

        required_skills = (
            jd_classification["required"]
        )

        optional_skills = (
            jd_classification["optional"]
        )

        print(
            "Required Skills:",
            required_skills
        )

        print(
            "Optional Skills:",
            optional_skills
        )

        # STEP 3 — Semantic Skill Matching
        matched_skills = (
            self.semantic_matcher
            .semantic_skill_match(
                resume_skills,
                jd_skills
            )
        )

        print(
            "Matched Skills:",
            matched_skills
        )

        # STEP 4 — Weighted Skill Gap Analysis
        weighted_result = (
            self.weighted_analyzer
            .analyze(
                required_skills,
                optional_skills,
                matched_skills
            )
        )

        print(
            "Weighted Skill Match:",
            weighted_result[
                "match_score"
            ]
        )

        # STEP 5 — Generate Embeddings
        jd_embedding = (
            self.embedding_service
            .get_embeddings(
                [job_description]
            )[0]
        )

        resume_embedding = (
            self.embedding_service
            .get_embeddings(
                [resume_text]
            )[0]
        )

        # STEP 6 — Document Similarity
        doc_score = float(
            cosine_similarity(
                [jd_embedding],
                [resume_embedding]
            )[0][0]
        )

        print(
            "Document Score:",
            doc_score
        )

        # STEP 7 — Final Combined Score
        skill_score = (
            weighted_result[
                "match_score"
            ] / 100
        )

        final_score = (
            skill_score * 0.7
            + doc_score * 0.3
        )

        final_percent = round(
            final_score * 100,
            2
        )

        print(
            "Final Score:",
            final_percent
        )

        # STEP 8 — Generate Explanation
        all_missing = (
            weighted_result[
                "missing_required"
            ]
            +
            weighted_result[
                "missing_optional"
            ]
        )

        explanation = (
            self.explainer
            .generate_explanation(
                matched_skills=matched_skills,
                missing_skills=all_missing,
                match_score=final_percent
            )
        )

        # STEP 9 — Final Output
        return {
            "required_skills":
                required_skills,
            "optional_skills":
                optional_skills,
            "matched_skills":
                matched_skills,
            "missing_required":
                weighted_result[
                    "missing_required"
                ],
            "missing_optional":
                weighted_result[
                    "missing_optional"
                ],
            "recommendations":
                weighted_result[
                    "recommendations"
                ],
            "required_match":
                weighted_result[
                    "required_match"
                ],
            "optional_match":
                weighted_result[
                    "optional_match"
                ],
            "skill_score":
                weighted_result[
                    "match_score"
                ],
            "document_score":
                round(
                    float(doc_score) * 100,
                    2
                ),
            "final_score":
                final_percent,
            "summary":
                explanation["summary"],
            "strong_matches":
                explanation[
                    "strong_matches"
                ],
            "learning_recommendations":
                explanation[
                    "recommendations"
                ]
        }