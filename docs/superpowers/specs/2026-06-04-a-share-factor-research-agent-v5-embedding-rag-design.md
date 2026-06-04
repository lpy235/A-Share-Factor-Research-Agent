# A-Share Factor Research Agent V5 Embedding RAG Design

## Goal

V5 upgrades retrieval from keyword-only chunk search to embedding-backed RAG.

The workflow should still run offline. The first embedding backend is a deterministic hashing embedder that turns text into normalized vectors. This makes the project reliable in tests and demos while leaving room for sentence-transformers or ChromaDB later.

## Scope

In scope:

- Add local deterministic text embeddings.
- Add vector similarity retrieval over document chunks.
- Add `retrieval_mode` with `keyword`, `vector`, and `hybrid`.
- Use `hybrid` as the default retrieval mode.
- Store compact retrieval diagnostics in graph state and trace payloads.
- Preserve all V4 source modes: `upload`, `auto`, `hybrid`.

Out of scope:

- Downloading embedding models.
- Persistent vector database.
- ChromaDB collection management.
- Cross-encoder reranking.

## Architecture

```text
sources
-> SimpleChunker
-> KeywordRetriever
-> HashingTextEmbedder
-> VectorRetriever
-> HybridRetriever
-> retrieved chunks with diagnostics
-> factor hypothesis extraction
```

The retrieval layer lives under `app/rag`:

```text
app/rag/embeddings.py
app/rag/vector_retriever.py
```

`RetrieveChunksNode` chooses the retriever by `state["retrieval_mode"]`.

## Retrieval Modes

```text
keyword: current token-overlap retriever
vector: cosine similarity over hashing embeddings
hybrid: combine keyword and vector scores, then deduplicate chunks
```

Default:

```text
hybrid
```

The API accepts:

```python
retrieval_mode: str = "hybrid"
embedding_dim: int = 256
```

## Success Criteria

- Existing V4 tests continue to pass.
- Vector retrieval returns semantically relevant chunks for A-share factor queries.
- Hybrid retrieval keeps deterministic behavior and preserves V4 factor extraction.
- `/runs/{run_id}/events` includes retrieval mode and retrieved chunk count.
- The project still runs without model downloads or external API keys.

