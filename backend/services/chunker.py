from langchain_text_splitters import RecursiveCharacterTextSplitter

class TextChunker:
    """
    Handles text chunking for embedding.
    Uses recursive splitting to preserve meaning.
    """

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100
    ):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

    def chunk_text(self, text: str):
        """
        Split text into chunks.
        """

        if not text:
            return []

        chunks = self.splitter.split_text(text)

        return chunks