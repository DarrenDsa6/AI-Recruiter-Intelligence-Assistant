from sentence_transformers import SentenceTransformer
import numpy as np

from services.retriever import RetrieverService
from services.skills import SkillExtractionService

class MatcherService:
    def __init__(self):
        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.retriever = RetrieverService()
        self.skill_extractor = SkillExtractionService()

    def compute_similarity(self, jd_text, top_k=10):
        jd_text = jd_text.strip()
        results = self.retriever.search(
            query=jd_text,
            top_k=top_k
        )
        if not results:
            return {
                "match_score": 0,
                "matched_skills": [],
                "missing_skills": []
            }

        # Extract JD skills
        jd_skills = self.skill_extractor.extract_skills(
            jd_text
        )

        combined_text = ""
        for item in results:
            combined_text += item["text"]

        # Extract Resume/GitHub skills
        candidate_skills = self.skill_extractor.extract_skills(
            combined_text
        )

        jd_set = set(jd_skills)
        candidate_set = set(candidate_skills)
        matched_skills = list(
            jd_set.intersection(candidate_set)
        )

        missing_skills = list(
            jd_set.difference(candidate_set)
        )

        if len(jd_set) == 0:
            match_score = 0
        else:
            match_score = round(
                (len(matched_skills) / len(jd_set)) * 100,
                2
            )

        return {
            "match_score": match_score,
            "matched_skills": matched_skills,
            "missing_skills": missing_skills
        }