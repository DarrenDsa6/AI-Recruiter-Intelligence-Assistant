import json
import re
import os

class SkillExtractionService:
    def __init__(self):
        base_path = os.path.dirname(__file__)
        # Load skills list
        skills_path = os.path.abspath(
            os.path.join(
                base_path,
                "..",
                "data",
                "skills.json"
            )
        )

        with open(skills_path, "r") as f:
            self.skills_list = json.load(f)

        # Load alias mapping
        alias_path = os.path.abspath(
            os.path.join(
                base_path,
                "..",
                "data",
                "skill_aliases.json"
            )
        )

        with open(alias_path, "r") as f:
            self.alias_map = json.load(f)

        # Normalize skills once
        self.skills_list = [
            skill.lower().strip()
            for skill in self.skills_list
        ]

        # Remove risky short skills
        self.skills_list = [
            skill
            for skill in self.skills_list
            if len(skill) > 2
        ]

        # Precompile regex patterns
        self.skill_patterns = []

        for skill in self.skills_list:
            pattern = re.compile(
                r"\b"
                + re.escape(skill)
                + r"\b",
                re.IGNORECASE
            )

            self.skill_patterns.append(
                (skill, pattern)
            )

        # Alias patterns
        self.alias_patterns = []

        for alias, main_skill in self.alias_map.items():
            alias = alias.lower().strip()
            if len(alias) <= 2:
                continue
            pattern = re.compile(
                r"\b"
                + re.escape(alias)
                + r"\b",
                re.IGNORECASE
            )

            self.alias_patterns.append(
                (alias, main_skill, pattern)
            )

    def normalize_skill(self, skill):
        skill = skill.lower().strip()
        if skill in self.alias_map:
            return self.alias_map[skill]

        return skill

    def extract_skills(self, text):
        text = text.lower()
        detected_skills = set()

        # Match main skills
        for skill, pattern in self.skill_patterns:
            if pattern.search(text):
                normalized = self.normalize_skill(skill)
                detected_skills.add(normalized)

        # Match alias skills
        for alias, main_skill, pattern in self.alias_patterns:
            if pattern.search(text):
                detected_skills.add(main_skill)

        return list(detected_skills)