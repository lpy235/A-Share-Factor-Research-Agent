from dataclasses import dataclass

from app.rag.chunker import DocumentChunk
from app.rag.embeddings import HashingTextEmbedder
from app.rag.retriever import KeywordRetriever, tokenize


@dataclass(frozen=True)
class RetrievalResult:
    chunk: DocumentChunk
    score: float
    method: str


class VectorRetriever:
    def __init__(self, chunks: list[DocumentChunk], embedder: HashingTextEmbedder | None = None) -> None:
        self.chunks = chunks
        self.embedder = embedder or HashingTextEmbedder()
        self.chunk_vectors = self.embedder.embed_many([chunk.text for chunk in chunks])

    def search_with_scores(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        query_vector = self.embedder.embed(query)
        scored: list[RetrievalResult] = []
        for chunk, chunk_vector in zip(self.chunks, self.chunk_vectors, strict=True):
            score = float(query_vector @ chunk_vector)
            if score > 0:
                scored.append(RetrievalResult(chunk=chunk, score=score, method="vector"))
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:top_k]

    def search(self, query: str, top_k: int = 5) -> list[DocumentChunk]:
        return [item.chunk for item in self.search_with_scores(query, top_k)]


class HybridRetriever:
    def __init__(self, chunks: list[DocumentChunk], embedder: HashingTextEmbedder | None = None) -> None:
        self.chunks = chunks
        self.embedder = embedder or HashingTextEmbedder()

    def search_with_scores(self, query: str, top_k: int = 5) -> list[RetrievalResult]:
        scores: dict[str, RetrievalResult] = {}
        keyword_results = self._keyword_scores(query)
        vector_results = VectorRetriever(self.chunks, self.embedder).search_with_scores(
            query,
            top_k=max(top_k * 2, top_k),
        )

        for chunk, score in keyword_results:
            scores[chunk.chunk_id] = RetrievalResult(chunk=chunk, score=score, method="keyword")

        for result in vector_results:
            current = scores.get(result.chunk.chunk_id)
            if current is None:
                scores[result.chunk.chunk_id] = RetrievalResult(
                    chunk=result.chunk,
                    score=result.score,
                    method="vector",
                )
            else:
                scores[result.chunk.chunk_id] = RetrievalResult(
                    chunk=result.chunk,
                    score=current.score + result.score,
                    method="hybrid",
                )

        ranked = list(scores.values())
        ranked.sort(key=lambda item: item.score, reverse=True)
        return ranked[:top_k]

    def search(self, query: str, top_k: int = 5) -> list[DocumentChunk]:
        return [item.chunk for item in self.search_with_scores(query, top_k)]

    def _keyword_scores(self, query: str) -> list[tuple[DocumentChunk, float]]:
        query_tokens = tokenize(query)
        scored: list[tuple[DocumentChunk, float]] = []
        for chunk in KeywordRetriever(self.chunks).search(query, top_k=len(self.chunks)):
            overlap = len(query_tokens & tokenize(chunk.text))
            if overlap > 0:
                scored.append((chunk, float(overlap)))
        return scored
