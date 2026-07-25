import logging

from config.constants import DOC_EMBEDDING_MODEL
from services.embedding.model_registry import ModelRegistry

logger = logging.getLogger(__name__)


class EmbedderService:
    def __init__(self):
        self.model = ModelRegistry.get(DOC_EMBEDDING_MODEL)
        self._cache: dict[str, object] = {}

    def embed_documents(self, documents: list[str]) -> list[list[float]]:
        embeddings = self.model.encode(documents, normalize_embeddings=True)
        return embeddings.tolist()

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        embeddings = []
        new_texts = []
        new_keys = []

        for text in texts:
            key = text.lower().strip()
            if key in self._cache:
                vec = self._cache[key]
                embeddings.append(vec.tolist() if hasattr(vec, "tolist") else list(vec))
            else:
                new_texts.append(key)
                new_keys.append(key)
                embeddings.append(None)

        if new_texts:
            logger.info(f"Embedding {len(new_texts)} new texts")
            new_vectors = self.model.encode(new_texts, normalize_embeddings=True)
            idx = 0
            for i in range(len(embeddings)):
                if embeddings[i] is None:
                    vec = new_vectors[idx]
                    self._cache[new_keys[idx]] = vec
                    embeddings[i] = vec.tolist() if hasattr(vec, "tolist") else list(vec)
                    idx += 1

        return embeddings


embedder = EmbedderService()
