from sentence_transformers import SentenceTransformer
import numpy as np

from services.retriever import RetrieverService

class MatcherService:
    def __init__(self):
        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.retriever = RetrieverService()

    def compute_similarity(self, jd_text, top_k=10):
        # Search relevant resume/github content
        results = self.retriever.search(
            query=jd_text,
            top_k=top_k
        )

        if not results:
            return {
                "match_score": 0,
                "matches": []
            }

        # Embed JD
        jd_embedding = self.model.encode(
            jd_text
        )

        similarities = []
        matched_texts = []

        # Compare similarity
        for item in results:
            text = item["text"]
            text_embedding = self.model.encode(
                text
            )
            similarity = np.dot(jd_embedding,text_embedding) / (
                np.linalg.norm(jd_embedding)* np.linalg.norm(text_embedding))

            similarities.append(similarity)
            matched_texts.append(text)

        # Average similarity
        avg_similarity = float(
            np.mean(similarities)
        )

        match_score = round(
            avg_similarity * 100,
            2
        )

        return {
            "match_score": match_score,
            "top_matches": matched_texts[:5]
        }