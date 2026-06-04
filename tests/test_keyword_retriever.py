from app.rag.chunker import DocumentChunk
from app.rag.retriever import KeywordRetriever


def test_keyword_retriever_returns_relevant_chunks_first():
    chunks = [
        DocumentChunk("c1", "a.md", "user_upload", "本文讨论动量因子和过去收益率。"),
        DocumentChunk("c2", "b.md", "user_upload", "本文讨论股息率和基本面。"),
        DocumentChunk("c3", "c.md", "user_upload", "量价齐升可能产生趋势延续。"),
    ]
    result = KeywordRetriever(chunks).search("动量 量价 趋势", top_k=2)
    assert len(result) == 2
    assert result[0].chunk_id in {"c1", "c3"}

