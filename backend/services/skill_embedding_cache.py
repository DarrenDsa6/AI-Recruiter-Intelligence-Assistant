import pickle
import os

from sentence_transformers import SentenceTransformer

class SkillEmbeddingCache:
    def __init__(self):
        print("Loading embedding model for cache...")
        self.model = SentenceTransformer(
            "BAAI/bge-small-en-v1.5"
        )
        self.cache_path = "data/skill_embeddings.pkl"
        self.embeddings = {}
        self.load_cache()

    def load_cache(self):
        if os.path.exists(self.cache_path):
            with open(self.cache_path, "rb") as f:
                self.embeddings = pickle.load(f)
            print(
                f"Loaded {len(self.embeddings)} skill embeddings."
            )
        else:
            print("No existing cache found.")

    def save_cache(self):
        with open(self.cache_path, "wb") as f:
            pickle.dump(self.embeddings, f)
        print(
            f"Saved {len(self.embeddings)} embeddings."
        )

    def build_cache(self, skills):
        new_skills = [
            skill
            for skill in skills
            if skill not in self.embeddings
        ]
        if not new_skills:
            print("All skills already cached.")
            return
        print(
            f"Embedding {len(new_skills)} new skills..."
        )
        texts = [
            "Represent this sentence for similarity: "
            + skill
            for skill in new_skills
        ]
        vectors = self.model.encode(
            texts,
            normalize_embeddings=True
        )

        for skill, vec in zip(new_skills, vectors):
            self.embeddings[skill] = vec

        self.save_cache()

    def get_embedding(self, skill):
        return self.embeddings.get(skill)