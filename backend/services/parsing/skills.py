import re
import json
import os
import logging

logger = logging.getLogger(__name__)

_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


class SkillExtractionService:
    def __init__(self):
        skills_path = os.path.join(_DATA_DIR, "skills.json")
        alias_path = os.path.join(_DATA_DIR, "skill_aliases.json")

        with open(skills_path, "r") as f:
            self.skills_list = [s.lower().strip() for s in json.load(f) if len(s.strip()) > 2]

        with open(alias_path, "r") as f:
            self.alias_map = json.load(f)

        self.skill_patterns = [
            (skill, re.compile(r"\b" + re.escape(skill) + r"\b", re.IGNORECASE))
            for skill in self.skills_list
        ]

        self.alias_patterns = [
            (alias.lower().strip(), main_skill, re.compile(r"\b" + re.escape(alias.lower().strip()) + r"\b", re.IGNORECASE))
            for alias, main_skill in self.alias_map.items()
            if len(alias.strip()) > 2
        ]

    def normalize_skill(self, skill: str) -> str:
        skill = skill.lower().strip()
        return self.alias_map.get(skill, skill)

    def extract_skills(self, text: str) -> list[str]:
        text_lower = text.lower()
        detected: set[str] = set()

        for skill, pattern in self.skill_patterns:
            if pattern.search(text_lower):
                detected.add(self.normalize_skill(skill))

        for alias, main_skill, pattern in self.alias_patterns:
            if pattern.search(text_lower):
                detected.add(main_skill)

        return list(detected)
