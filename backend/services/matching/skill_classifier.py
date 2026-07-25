import re


class JDSkillClassifier:
    REQUIRED_KEYWORDS = ["required", "must have", "mandatory"]
    OPTIONAL_KEYWORDS = ["preferred", "nice to have", "good to have"]

    def classify_skills(self, jd_text: str, extracted_skills: list[str]) -> dict:
        jd_lower = jd_text.lower()
        lines = jd_lower.split("\n")

        required_skills: set[str] = set()
        optional_skills: set[str] = set()
        mode = "required"

        for line in lines:
            line = line.strip()
            if any(kw in line for kw in self.REQUIRED_KEYWORDS):
                mode = "required"
                continue
            if any(kw in line for kw in self.OPTIONAL_KEYWORDS):
                mode = "optional"
                continue

            for skill in extracted_skills:
                if re.search(r"\b" + re.escape(skill) + r"\b", line):
                    if mode == "required":
                        required_skills.add(skill)
                    else:
                        optional_skills.add(skill)

        if not required_skills:
            required_skills = set(extracted_skills)

        return {"required": list(required_skills), "optional": list(optional_skills)}
