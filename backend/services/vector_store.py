import chromadb
import uuid

class VectorStoreService:
    def __init__(self):
        self.client = chromadb.Client(
            settings=chromadb.Settings(
                persist_directory="chroma_db"
            )
        )
        self.collection = self.client.get_or_create_collection(
            name="ai_recruiter_collection"
        )

    def add_documents(self, documents, embeddings, metadatas=None, session_id=None):
        if not documents:
            raise ValueError("No documents provided")

        if not embeddings:
            raise ValueError("Embeddings are empty")

        if len(documents) != len(embeddings):
            raise ValueError("Mismatch: documents vs embeddings")

        if metadatas and len(documents) != len(metadatas):
            raise ValueError("Mismatch: documents vs metadatas")

        if not session_id:
            session_id = str(uuid.uuid4())

        ids = [str(uuid.uuid4()) for _ in documents]

        final_metadatas = []

        for i in range(len(documents)):
            meta = {
                "session_id": session_id,
                "chunk_index": i
            }

            if metadatas:
                meta.update(metadatas[i])

            final_metadatas.append(meta)

        self.collection.add(
            documents=documents,
            embeddings=embeddings,
            ids=ids,
            metadatas=final_metadatas
        )

        return session_id

    def get_session_text(self, session_id):
        results = self.collection.get(
            where={"session_id": session_id}
        )

        docs = results.get("documents", [])

        if not docs:
            return ""

        return " ".join(docs)

    def delete_by_session(self, session_id):
        results = self.collection.get(
            where={"session_id": session_id}
        )

        ids = results.get("ids", [])
        if not ids:
            return 0

        self.collection.delete(ids=ids)
        return len(ids)

    def get_by_session(self, session_id):
        results = self.collection.get(
            where={"session_id": session_id},
            include=["documents", "embeddings", "metadatas"]
        )
        return results

    def query_by_session(self, session_id, query_embedding, top_k=5):
        results = self.collection.query(
            query_embeddings=[query_embedding],
            where={"session_id": session_id},
            n_results=top_k,
            include=["documents", "distances", "metadatas"]
        )
        return results


vector_store = VectorStoreService()
