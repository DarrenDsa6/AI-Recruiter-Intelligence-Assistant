import logging

logger = logging.getLogger(__name__)


class CrossEncoderReranker:
    """Re-ranks candidate resumes using a cross-encoder model for more accurate relevance scoring."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self._model = None

    def _lazy_load(self):
        if self._model is None:
            try:
                from sentence_transformers import CrossEncoder
                self._model = CrossEncoder(self.model_name)
                logger.info(f"Loaded cross-encoder model: {self.model_name}")
            except Exception as e:
                logger.warning(f"Failed to load cross-encoder model: {e}. Using fallback scoring.")
                self._model = None

    def rerank(self, query: str, documents: list[str], top_k: int = None) -> list[dict]:
        if not documents:
            return []

        self._lazy_load()
        if self._model is not None:
            pairs = [[query, doc] for doc in documents]
            try:
                scores = self._model.predict(pairs)
                results = [
                    {"index": i, "text": documents[i], "score": float(score)}
                    for i, score in enumerate(scores)
                ]
            except Exception as e:
                logger.error(f"Cross-encoder prediction failed: {e}")
                results = [
                    {"index": i, "text": documents[i], "score": 0.0}
                    for i in range(len(documents))
                ]
        else:
            results = [
                {"index": i, "text": documents[i], "score": 0.0}
                for i in range(len(documents))
            ]

        results.sort(key=lambda x: x["score"], reverse=True)
        if top_k and top_k < len(results):
            results = results[:top_k]
        return results

    def rerank_with_explanations(self, query: str, documents: list[dict], top_k: int = None) -> list[dict]:
        texts = [d.get("text", "") for d in documents]
        reranked = self.rerank(query, texts, top_k=None)
        for r, d in zip(reranked, documents):
            r.update(d)
        reranked.sort(key=lambda x: x["score"], reverse=True)
        if top_k and top_k < len(reranked):
            reranked = reranked[:top_k]
        return reranked


reranker = CrossEncoderReranker()
