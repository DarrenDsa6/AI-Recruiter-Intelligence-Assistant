import json

from services.skill_embedding_cache import SkillEmbeddingCache

def load_skills():
    with open("data/skills.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # If JSON is list
    if isinstance(data, list):
        return data

    # If JSON has key like {"skills": [...]}
    if "skills" in data:
        return data["skills"]

    return []

def main():
    skills = load_skills()
    print(f"Loaded {len(skills)} skills")
    cache = SkillEmbeddingCache()
    cache.build_cache(skills)

if __name__ == "__main__":
    main()