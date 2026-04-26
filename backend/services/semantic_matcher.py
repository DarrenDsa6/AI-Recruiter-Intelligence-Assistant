import numpy as np
from sentence_transformers import SentenceTransformer
from services.skill_embedding_cache import SkillEmbeddingCache

class SemanticMatcher:
    def __init__(self):
        print("Initializing Semantic Matcher...")
        # Load embedding model
        self.model = SentenceTransformer(
            "BAAI/bge-small-en-v1.5"
        )
        # Load cached embeddings
        self.cache = SkillEmbeddingCache()
        print(
            f"Loaded {len(self.cache.embeddings)} cached skill embeddings."
        )

    def get_cached_embeddings(self, skills):
        # Normalize skills
        skills = [
            skill.lower().strip()
            for skill in skills
        ]

        vectors = []
        missing_skills = []
        missing_indices = []

        # First pass — preserve order
        for idx, skill in enumerate(skills):
            vec = self.cache.get_embedding(skill)
            if vec is not None:
                vectors.append(vec)
            else:
                vectors.append(None)
                missing_skills.append(skill)
                missing_indices.append(idx)

        # Embed missing ones
        if missing_skills:
            print(
                f"Embedding {len(missing_skills)} uncached skills..."
            )
            texts = [
                "Represent this sentence for similarity: "
                + skill
                for skill in missing_skills
            ]
            new_vectors = self.model.encode(
                texts,
                normalize_embeddings=True
            )

            # Fill correct positions
            for idx, skill, vec in zip(
                missing_indices,
                missing_skills,
                new_vectors
            ):
                self.cache.embeddings[skill] = vec
                vectors[idx] = vec
            self.cache.save_cache()

        return np.array(vectors)

    def semantic_skill_match(
        self,
        resume_skills,
        jd_skills,
        threshold=0.90   # Increased threshold
    ):
        if not resume_skills or not jd_skills:
            return []

        # Normalize
        resume_skills = [
            skill.lower().strip()
            for skill in resume_skills
        ]

        jd_skills = [
            skill.lower().strip()
            for skill in jd_skills
        ]

        # Get embeddings
        resume_vecs = self.get_cached_embeddings(
            resume_skills
        )

        jd_vecs = self.get_cached_embeddings(
            jd_skills
        )

        # Cosine similarity (since normalized)
        similarity_matrix = np.dot(
            resume_vecs,
            jd_vecs.T
        )

        matches = set()

        # Debug logging
        for i in range(len(resume_skills)):

            for j in range(len(jd_skills)):

                score = similarity_matrix[i][j]

                if score >= threshold:

                    print(
                        f"MATCH: {resume_skills[i]} "
                        f"≈ {jd_skills[j]} "
                        f"({score:.3f})"
                    )

                    matches.add(jd_skills[j])

        return list(matches)