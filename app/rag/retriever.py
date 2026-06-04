import re

from app.rag.chunker import DocumentChunk


def tokenize(text: str) -> set[str]:
    chinese = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    english = re.findall(r"[A-Za-z0-9_]+", text.lower())
    tokens = set(english)
    for item in chinese:
        tokens.update(item[i : i + 2] for i in range(max(1, len(item) - 1)))
    return tokens


class KeywordRetriever:
    def __init__(self, chunks: list[DocumentChunk]) -> None:
        self.chunk_tokens = [(chunk, tokenize(chunk.text)) for chunk in chunks]

    def search(self, query: str, top_k: int = 5) -> list[DocumentChunk]:
        query_tokens = tokenize(query)
        scored: list[tuple[int, DocumentChunk]] = []
        for chunk, tokens in self.chunk_tokens:
            score = len(query_tokens & tokens)
            if score > 0:
                scored.append((score, chunk))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [chunk for _, chunk in scored[:top_k]]

