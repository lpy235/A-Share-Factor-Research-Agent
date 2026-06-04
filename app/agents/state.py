from typing import Any, Literal, TypedDict


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
    hypotheses: list[dict]
    factor_specs: list[dict]
    validation_results: list[dict]
    market_data_summary: dict
    metrics: list[dict]
    report_markdown: str
    selected_factors: list[str]
    warnings: list[str]
    errors: list[dict]
    trace: list[dict]
    event_db_path: str
    _market_data: Any
    _factor_values: dict[str, Any]
