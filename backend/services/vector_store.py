import chromadb
import uuid


class VectorStoreService:
    def __init__(self):
        self.client = chromadb.Client(
            settings=chromadb.Settings(anonymized_telemetry=False)
        )
        self.collection = self.client.get_or_create_collection(
            name="candidate_resumes"
        )

    def add_documents(self, documents, embeddings, metadatas=None, resume_id=None):
        if not documents:
            raise ValueError("No documents provided")
        if not embeddings:
            raise ValueError("Embeddings are empty")
        if len(documents) != len(embeddings):
            raise ValueError("Mismatch: documents vs embeddings")
        if metadatas and len(documents) != len(metadatas):
            raise ValueError("Mismatch: documents vs metadatas")
        if not resume_id:
            resume_id = str(uuid.uuid4())

        ids = [str(uuid.uuid4()) for _ in documents]
        final_metadatas = []
        for i in range(len(documents)):
            meta = {"resume_id": resume_id, "chunk_index": i}
            if metadatas:
                meta.update(metadatas[i])
            final_metadatas.append(meta)

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=final_metadatas
        )
        return resume_id

    def get_resume_text(self, resume_id):
        results = self.collection.get(where={"resume_id": resume_id})
        docs = results.get("documents", [])
        return " ".join(docs) if docs else ""

    def delete_by_resume(self, resume_id):
        results = self.collection.get(where={"resume_id": resume_id})
        ids = results.get("ids", [])
        if not ids:
            return 0
        self.collection.delete(ids=ids)
        return len(ids)

    def get_by_resume(self, resume_id):
        return self.collection.get(
            where={"resume_id": resume_id},
            include=["documents", "embeddings", "metadatas"]
        )

    def query_by_resume(self, resume_id, query_embedding, top_k=5):
        return self.collection.query(
            query_embeddings=[query_embedding],
            where={"resume_id": resume_id},
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )

    def delete_all(self):
        self.client.delete_collection("candidate_resumes")
        self.collection = self.client.get_or_create_collection(
            name="candidate_resumes"
        )

    # Backward-compatible aliases (deprecated, will be removed in Phase 3)
    def add_documents_legacy(self, documents, embeddings, metadatas=None, session_id=None):
        return self.add_documents(documents, embeddings, metadatas, resume_id=session_id)

    def get_by_session(self, session_id):
        return self.get_by_resume(session_id)

    def query_by_session(self, session_id, query_embedding, top_k=5):
        return self.query_by_resume(session_id, query_embedding, top_k)

    def delete_by_session(self, session_id):
        return self.delete_by_resume(session_id)

    def get_session_text(self, session_id):
        return self.get_resume_text(session_id)


vector_store = VectorStoreService()
