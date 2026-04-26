import re

class JDSkillClassifier:
    def classify_skills(self, jd_text, extracted_skills):
        jd_text = jd_text.lower()

        required_keywords = [
            "required",
            "must have",
            "mandatory"
        ]

        optional_keywords = [
            "preferred",
            "nice to have",
            "good to have"
        ]

        required_skills = set()
        optional_skills = set()
        lines = jd_text.split("\n")
        mode = "required"

        for line in lines:
            line = line.strip()
            if any(
                key in line
                for key in required_keywords
            ):
                mode = "required"
                continue

            if any(
                key in line
                for key in optional_keywords
            ):
                mode = "optional"
                continue

            # Match extracted skills in line
            for skill in extracted_skills:
                pattern = r"\b" + re.escape(skill) + r"\b"
                if re.search(pattern, line):
                    if mode == "required":
                        required_skills.add(skill)
                    else:
                        optional_skills.add(skill)

        # Fallback
        if not required_skills:
            required_skills = set(
                extracted_skills
            )

        return {
            "required": list(required_skills),
            "optional": list(optional_skills)
        }