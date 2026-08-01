import logging
import json

logger = logging.getLogger(__name__)


class MetaAgent:
    """The Judge: takes outputs from Technical and HR agents, compares against JD, generates final score."""

    async def evaluate(
        self,
        technical_analysis: dict,
        hr_analysis: dict,
        match_result: dict,
        job_description: str,
        llm_client,
    ) -> dict:
        agent_summary = self._create_summary(technical_analysis, hr_analysis, match_result)
        llm_score = await self._llm_evaluation(agent_summary, job_description, llm_client)

        final_score = self._compute_final_score(match_result, llm_score, hr_analysis)
        pros, cons = self._generate_assessment(
            match_result, technical_analysis, hr_analysis, llm_score
        )

        return {
            "final_score": final_score,
            "technical_score": technical_analysis.get("overall_score", match_result.get("document_score", 0)),
            "hr_score": hr_analysis.get("career_progression_score", 50),
            "agent_summary": agent_summary,
            "llm_verdict": llm_score,
            "pros": pros,
            "cons": cons,
            "recommendation": self._recommendation(final_score),
        }

    def _create_summary(self, technical: dict, hr: dict, match: dict) -> dict:
        return {
            "technical": {
                "repos": technical.get("repo_count", 0),
                "stars": technical.get("total_stars", 0),
                "top_languages": technical.get("top_languages", []),
                "llm_analysis": technical.get("llm_analysis", {}),
            },
            "hr": {
                "tenure_years": hr.get("estimated_tenure_years", 0),
                "progression_score": hr.get("career_progression_score", 0),
                "education": hr.get("education", {}),
                "positions_held": hr.get("positions_held", 0),
            },
            "match": {
                "matched_skills": match.get("matched_skills", []),
                "missing_required": match.get("missing_required", []),
                "skill_score": match.get("skill_score", 0),
                "document_score": match.get("document_score", 0),
                "final_score": match.get("final_score", 0),
            },
        }

    async def _llm_evaluation(self, agent_summary: dict, jd: str, llm_client) -> dict:
        try:
            return await llm_client.judge_candidate(agent_summary, jd)
        except Exception as e:
            logger.warning(f"MetaAgent LLM evaluation failed: {e}")
            return {"score": 50, "reasoning": "LLM evaluation failed", "strengths": [], "weaknesses": []}

    def _compute_final_score(self, match_result: dict, llm_score: dict, hr_analysis: dict) -> float:
        match_score = match_result.get("final_score", 0)
        llm_raw = llm_score.get("score", 50) if isinstance(llm_score, dict) else 50
        progression = hr_analysis.get("career_progression_score", 50)

        weighted = (match_score * 0.5) + (llm_raw * 0.3) + (progression * 0.2)
        return round(min(100, max(0, weighted)), 2)

    def _generate_assessment(
        self, match_result: dict, technical: dict, hr: dict, llm_score: dict
    ) -> tuple[list[dict], list[dict]]:
        pros = []
        cons = []

        for skill in match_result.get("matched_skills", [])[:5]:
            pros.append({"type": "skill_match", "detail": f"Matches required skill: {skill}"})

        if technical.get("repo_count", 0) > 5:
            pros.append({"type": "github_activity", "detail": "Strong GitHub activity with multiple repositories"})

        if technical.get("total_stars", 0) > 10:
            pros.append({"type": "github_impact", "detail": "Repositories have significant community traction"})

        if hr.get("estimated_tenure_years", 0) >= 5:
            pros.append({"type": "experience", "detail": f"Solid experience ({hr['estimated_tenure_years']} years)"})

        for skill in match_result.get("missing_required", [])[:5]:
            cons.append({"type": "missing_skill", "detail": f"Missing required skill: {skill}"})

        if hr.get("estimated_tenure_years", 0) < 2:
            cons.append({"type": "limited_experience", "detail": "Limited professional experience"})

        if isinstance(llm_score, dict):
            for w in llm_score.get("weaknesses", []):
                cons.append({"type": "llm_identified_gap", "detail": w})
            for s in llm_score.get("strengths", []):
                pros.append({"type": "llm_identified_strength", "detail": s})

        return pros, cons

    def _recommendation(self, score: float) -> str:
        if score >= 80:
            return "strong_yes"
        elif score >= 60:
            return "yes"
        elif score >= 40:
            return "maybe"
        else:
            return "no"
