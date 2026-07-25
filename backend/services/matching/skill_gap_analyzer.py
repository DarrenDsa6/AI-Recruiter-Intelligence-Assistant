REQUIRED_WEIGHT = 0.7
OPTIONAL_WEIGHT = 0.3


class WeightedSkillGapAnalyzer:
    def analyze(
        self,
        required_skills: list[str],
        optional_skills: list[str],
        matched_skills: list[str],
    ) -> dict:
        required_set = {s.lower() for s in required_skills}
        optional_set = {s.lower() for s in optional_skills}
        matched_set = {s.lower() for s in matched_skills}

        matched_required = required_set & matched_set
        matched_optional = optional_set & matched_set

        missing_required = list(required_set - matched_required)
        missing_optional = list(optional_set - matched_optional)

        required_score = len(matched_required) / len(required_set) if required_set else 0
        optional_score = len(matched_optional) / len(optional_set) if optional_set else 0

        match_score = (required_score * REQUIRED_WEIGHT + optional_score * OPTIONAL_WEIGHT) * 100

        recommendations = [f"Required skill missing: {s}" for s in missing_required[:3]]
        recommendations += [f"Optional skill to learn: {s}" for s in missing_optional[:2]]

        return {
            "match_score": round(match_score, 2),
            "required_match": round(required_score * 100, 2),
            "optional_match": round(optional_score * 100, 2),
            "missing_required": missing_required,
            "missing_optional": missing_optional,
            "recommendations": recommendations,
        }
