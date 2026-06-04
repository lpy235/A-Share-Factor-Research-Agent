import hashlib

import numpy as np

from app.rag.retriever import tokenize


class HashingTextEmbedder:
    def __init__(self, dim: int = 256) -> None:
        if dim < 16:
            raise ValueError("embedding dim must be at least 16")
        self.dim = dim

    def embed(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dim, dtype=float)
        for token in tokenize(text):
            digest = hashlib.md5(token.encode("utf-8")).digest()
            bucket = int.from_bytes(digest[:4], byteorder="big") % self.dim
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            vector[bucket] += sign
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm

    def embed_many(self, texts: list[str]) -> list[np.ndarray]:
        return [self.embed(text) for text in texts]
