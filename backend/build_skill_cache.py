import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

from services.embedding import SkillEmbeddingCache

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


def load_skills() -> list[str]:
    with open(os.path.join(DATA_DIR, "skills.json"), "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        return data
    return data.get("skills", [])


def main():
    skills = load_skills()
    print(f"Loaded {len(skills)} skills")
    cache = SkillEmbeddingCache()
    cache.build_cache(skills)


if __name__ == "__main__":
    main()
