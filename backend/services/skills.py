import json
import re
import os

class SkillExtractionService:
    def __init__(self):
        # Load skills from JSON
        skills_path = os.path.join(
            os.path.dirname(__file__),
            "..",
            "data",
            "skills.json"
        )
        skills_path = os.path.abspath(skills_path)
        with open(skills_path, "r") as f:
            self.skills_list = json.load(f)

    def extract_skills(self, text):
        text = text.lower()
        detected_skills = set()
        for skill in self.skills_list:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text):
                detected_skills.add(skill)

        return list(detected_skills)