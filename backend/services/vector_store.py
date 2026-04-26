import chromadb
import uuid

class VectorStoreService:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path="chroma_db"
        )

        self.collection = self.client.get_or_create_collection(
            name="resume_collection"
        )

    def add_documents(self, documents, embeddings, metadata=None):
        resume_id = str(uuid.uuid4())

        ids = [str(uuid.uuid4()) for _ in documents]

        metadatas = []
        for i in range(len(documents)):
            meta = {
                "resume_id": resume_id,
                "chunk_index": i
            }
            if metadata:
                meta.update(metadata)
            metadatas.append(meta)

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

        return resume_id

    def get_resume_text(self, resume_id):
        results = self.collection.get(
            where={"resume_id": resume_id}
        )

        documents = results.get("documents", [])
        return " ".join(documents) if documents else ""

    def get_all_documents(self):
        return self.collection.get()

    def delete_resume(self, resume_id):
        results = self.collection.get(
            where={"resume_id": resume_id}
        )
        ids = results.get("ids", [])
        if not ids:
            return 0
        self.collection.delete(ids=ids)

        return len(ids)