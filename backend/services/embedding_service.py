import chromadb
from sentence_transformers import SentenceTransformer

class EmbeddingService:
    """
    Handles embedding generation and vector storage.
    Uses:
    - SentenceTransformers for embeddings
    - ChromaDB for vector storage
    """

    def __init__(self):

        # Load embedding model
        self.model = SentenceTransformer(
            "all-MiniLM-L6-v2"
        )

        # Create Chroma client
        self.client = chromadb.Client()

        # Create or load collection
        self.collection = self.client.get_or_create_collection(
            name="candidate_documents"
        )

    def generate_embeddings(self, chunks):

        embeddings = self.model.encode(
            chunks
        ).tolist()

        return embeddings

    def store_embeddings(
        self,
        chunks,
        metadata=None
    ):
        """
        Store chunks + embeddings
        """

        embeddings = self.generate_embeddings(
            chunks
        )

        ids = [
            f"chunk_{i}"
            for i in range(len(chunks))
        ]

        if metadata is None:
            metadata = [{} for _ in chunks]

        self.collection.add(
            documents=chunks,
            embeddings=embeddings,
            metadatas=metadata,
            ids=ids
        )

        return len(ids)