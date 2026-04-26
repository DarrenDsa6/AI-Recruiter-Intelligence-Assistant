class WeightedSkillGapAnalyzer:
    def analyze(self, required_skills,optional_skills, matched_skills):
        required_set = set(
            skill.lower()
            for skill in required_skills
        )

        optional_set = set(
            skill.lower()
            for skill in optional_skills
        )

        matched_set = set(
            skill.lower()
            for skill in matched_skills
        )

        matched_required = (
            required_set.intersection(
                matched_set
            )
        )

        matched_optional = (
            optional_set.intersection(
                matched_set
            )
        )

        missing_required = list(
            required_set - matched_required
        )

        missing_optional = list(
            optional_set - matched_optional
        )

        # Weights
        REQUIRED_WEIGHT = 0.7
        OPTIONAL_WEIGHT = 0.3

        if required_set:
            required_score = (
                len(matched_required)
                / len(required_set)
            )
        else:
            required_score = 0

        if optional_set:
            optional_score = (
                len(matched_optional)
                / len(optional_set)
            )
        else:
            optional_score = 0

        match_score = (
            required_score * REQUIRED_WEIGHT
            + optional_score * OPTIONAL_WEIGHT
        ) * 100

        recommendations = []

        for skill in missing_required[:3]:
            recommendations.append(
                f"Required skill missing: {skill}"
            )

        for skill in missing_optional[:2]:
            recommendations.append(
                f"Optional skill to learn: {skill}"
            )

        return {
            "match_score":
                round(match_score, 2),
            "required_match":
                round(required_score * 100, 2),
            "optional_match":
                round(optional_score * 100, 2),
            "missing_required":
                missing_required,
            "missing_optional":
                missing_optional,
            "recommendations":
                recommendations
        }