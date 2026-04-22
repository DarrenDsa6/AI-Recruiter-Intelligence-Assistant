import chromadb

class VectorStoreService:

    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="./chroma_db"
        )
        self.collection = self.client.get_or_create_collection(
            name="resumes"
        )

    def add_documents(self, documents, embeddings):
        ids = [
            str(i)
            for i in range(len(documents))
        ]
        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids
        )

        return len(ids)