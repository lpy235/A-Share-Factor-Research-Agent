from dataclasses import dataclass


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    source_title: str
    source_type: str
    text: str
    source_url: str | None = None


class SimpleChunker:
    def __init__(self, chunk_size: int = 800, overlap: int = 120) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(
        self,
        source_title: str,
        source_type: str,
        text: str,
        source_url: str | None = None,
    ) -> list[DocumentChunk]:
        chunks: list[DocumentChunk] = []
        start = 0
        index = 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            piece = text[start:end].strip()
            if piece:
                chunks.append(DocumentChunk(f"{source_title}:{index}", source_title, source_type, piece, source_url))
            if end == len(text):
                break
            start = max(0, end - self.overlap)
            index += 1
        return chunks

