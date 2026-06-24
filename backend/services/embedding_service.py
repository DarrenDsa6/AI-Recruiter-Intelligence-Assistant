from sentence_transformers import SentenceTransformer
import logging

logger = logging.getLogger(__name__)

class EmbedderService:
    def __init__(self):
        logger.info("Loading document embedding model...")
        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )
        self.embedding_cache = {}

    def embed_documents(self, documents):
        embeddings = self.model.encode(documents)
        return embeddings.tolist()

    def get_embeddings(self, texts):
        embeddings = []
        new_texts = []
        new_keys = []

        for text in texts:
            key = text.lower().strip()
            if key in self.embedding_cache:
                embeddings.append(self.embedding_cache[key])
            else:
                new_texts.append(key)
                new_keys.append(key)
                embeddings.append(None)

        if new_texts:
            logger.info(f"Embedding {len(new_texts)} new texts...")
            new_vectors = self.model.encode(new_texts, normalize_embeddings=True)
            idx = 0
            for i in range(len(embeddings)):
                if embeddings[i] is None:
                    vec = new_vectors[idx]
                    key = new_keys[idx]
                    self.embedding_cache[key] = vec
                    embeddings[i] = vec
                    idx += 1

        return embeddings


embedder = EmbedderService()
