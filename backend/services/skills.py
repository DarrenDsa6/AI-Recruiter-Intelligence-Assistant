import json
import re
import os


class SkillExtractionService:

    def __init__(self):
        base_path = os.path.dirname(__file__)

        # Load main skills list
        skills_path = os.path.abspath(
            os.path.join(base_path, "..", "data", "skills.json")
        )
        with open(skills_path, "r") as f:
            self.skills_list = json.load(f)

        # Load alias mapping
        alias_path = os.path.abspath(
            os.path.join(base_path, "..", "data", "skill_aliases.json")
        )
        with open(alias_path, "r") as f:
            self.alias_map = json.load(f)

    def normalize_skill(self, skill):
        skill = skill.lower().strip()
        if skill in self.alias_map:
            return self.alias_map[skill]

        return skill

    def extract_skills(self, text):
        text = text.lower()
        detected_skills = set()

        # Match main skills
        for skill in self.skills_list:
            pattern = r"\b" + re.escape(skill) + r"\b"
            if re.search(pattern, text):
                normalized = self.normalize_skill(skill)
                detected_skills.add(normalized)

        # Match alias skills
        for alias in self.alias_map.keys():
            pattern = r"\b" + re.escape(alias) + r"\b"
            if re.search(pattern, text):
                normalized = self.alias_map[alias]
                detected_skills.add(normalized)

        return list(detected_skills)