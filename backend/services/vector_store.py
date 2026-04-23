import chromadb
import uuid

class VectorStoreService:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="./chroma_db"
        )
        self.collection = self.client.get_or_create_collection(
            name="resumes"
        )

    def add_documents(self, documents, embeddings, metadatas=None):
        ids = [
            str(uuid.uuid4())
            for _ in documents
        ]

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

        return len(ids)