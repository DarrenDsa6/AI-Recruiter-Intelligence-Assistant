import chromadb
from sentence_transformers import SentenceTransformer

class RetrieverService:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="./chroma_db"
        )
        self.collection = self.client.get_or_create_collection(
            name="resumes"
        )
        self.model = SentenceTransformer(
            "sentence-transformers/all-MiniLM-L6-v2"
        )

    def search(self, query, top_k=5):
        query_embedding = self.model.encode(
            query
        ).tolist()

        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k
        )
        documents = results.get("documents", [[]])[0]
        return documents