from sentence_transformers import SentenceTransformer


class EmbedderService:
    def __init__(self):
        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    def embed_documents(self, documents):
        embeddings = self.model.encode(
            documents
        )
        return embeddings.tolist()