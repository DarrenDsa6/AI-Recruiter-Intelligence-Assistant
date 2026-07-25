from config.constants import CHUNK_SIZE, CHUNK_OVERLAP


class ChunkerService:
    def chunk_text(self, text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[dict]:
        chunks = []
        start = 0
        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunks.append({
                "text": text[start:end],
                "start": start,
                "end": end,
            })
            start += chunk_size - overlap
        return chunks
