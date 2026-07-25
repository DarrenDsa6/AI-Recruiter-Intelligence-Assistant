class MatchExplainer:
    def generate_explanation(
        self, matched_skills: list[str], missing_skills: list[str], match_score: float
    ) -> dict:
        strong_matches = matched_skills[:5]
        recommendations = [f"Consider learning {s}" for s in missing_skills[:5]]

        if match_score > 80:
            summary = "Your resume strongly matches this job description."
        elif match_score > 60:
            summary = "Your resume partially matches this job description."
        else:
            summary = "Your resume has limited match with this job description."

        return {
            "summary": summary,
            "strong_matches": strong_matches,
            "recommendations": recommendations,
        }
