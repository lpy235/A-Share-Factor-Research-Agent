import numpy as np

from app.rag.chunker import DocumentChunk
from app.rag.embeddings import HashingTextEmbedder
from app.rag.vector_retriever import HybridRetriever, VectorRetriever


def test_hashing_embedder_returns_normalized_deterministic_vector():
    embedder = HashingTextEmbedder(dim=64)

    first = embedder.embed("A股量价动量因子")
    second = embedder.embed("A股量价动量因子")

    assert np.allclose(first, second)
    assert np.isclose(np.linalg.norm(first), 1.0)


def test_vector_retriever_returns_relevant_chunk():
    chunks = [
        DocumentChunk("c1", "volume report", "public_article", "成交量放大且价格上涨，可构造量价动量因子。"),
        DocumentChunk("c2", "bond report", "public_article", "债券久期和利率风险研究。"),
    ]

    results = VectorRetriever(chunks, HashingTextEmbedder(dim=128)).search(
        "A股量价动量因子",
        top_k=1,
    )

    assert results[0].chunk_id == "c1"


def test_hybrid_retriever_deduplicates_keyword_and_vector_results():
    chunks = [
        DocumentChunk("c1", "volume report", "public_article", "成交量放大且价格上涨，可构造量价动量因子。"),
        DocumentChunk("c2", "volatility report", "public_article", "波动率可以刻画风险补偿。"),
    ]

    results = HybridRetriever(chunks, HashingTextEmbedder(dim=128)).search_with_scores(
        "A股量价动量因子",
        top_k=2,
    )

    assert len({item.chunk.chunk_id for item in results}) == len(results)
    assert results[0].chunk.chunk_id == "c1"
