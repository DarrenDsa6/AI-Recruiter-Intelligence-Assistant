class SkillGapAnalyzer:
    def analyze(self, resume_skills, jd_skills):
        # normalize (important)
        jd_set = set(skill.lower().strip() for skill in jd_skills)
        resume_set = set(skill.lower().strip() for skill in resume_skills)

        # matched skills (intersection)
        matched_set = jd_set & resume_set

        # missing skills
        missing_skills = jd_set - resume_set

        # match percentage (JD coverage)
        if len(jd_set) > 0:
            match_score = (len(matched_set) / len(jd_set)) * 100
        else:
            match_score = 0

        # recommendations
        recommendations = [
            f"Consider learning {skill}"
            for skill in list(missing_skills)[:5]
        ]

        return {
            "match_score": round(match_score, 2),
            "matched_skills": sorted(list(matched_set)),
            "missing_skills": sorted(list(missing_skills)),
            "resume_extra_skills": sorted(list(resume_set - jd_set)),
            "recommendations": recommendations
        }