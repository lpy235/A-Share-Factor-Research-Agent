from typing import Literal, TypedDict


class ResearchState(TypedDict, total=False):
    run_id: str
    research_topic: str
    source_mode: Literal["auto", "upload", "hybrid"]
    universe: str
    start_date: str
    end_date: str
    document_paths: list[str]
    max_chunks: int
    sources: list[dict]
    chunks: list[dict]
    factor_specs: list[dict]
    metrics: list[dict]
    report_markdown: str
    selected_factors: list[str]
    warnings: list[str]
