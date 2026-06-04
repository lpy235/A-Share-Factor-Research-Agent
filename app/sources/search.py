from app.rag.retriever import tokenize
from app.sources.source_policy import SourcePolicy


class ManualSourceSearch:
    def __init__(self, sources: list[dict[str, str]]) -> None:
        self.sources = sources
        self.policy = SourcePolicy()

    def search(self, query: str, max_sources: int = 5) -> list[dict[str, str]]:
        query_tokens = tokenize(query)
        results: list[tuple[int, dict[str, str]]] = []
        for source in self.sources:
            url = source.get("url", "")
            if not self.policy.check_url(url).allowed:
                continue
            score = len(query_tokens & tokenize(f"{source.get('title', '')} {url}"))
            if score > 0:
                results.append((score, source))
        results.sort(key=lambda item: item[0], reverse=True)
        return [source for _, source in results[:max_sources]]

