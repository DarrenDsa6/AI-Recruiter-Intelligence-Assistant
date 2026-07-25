from config.constants import CHUNK_SIZE, CHUNK_OVERLAP


class ChunkerService:
    def chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
        chunks = []
        start = 0
        while start < len(text):
            chunks.append(text[start : start + chunk_size])
            start += chunk_size - overlap
        return chunks
