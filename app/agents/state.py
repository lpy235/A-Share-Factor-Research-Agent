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
    max_sources: int
    allow_live_fetch: bool
    retrieval_mode: Literal["keyword", "vector", "hybrid"]
    embedding_dim: int
    retrieval_diagnostics: dict
    extraction_mode: Literal["rule", "llm", "hybrid"]
    enable_llm_extraction: bool
    llm_retry_count: int
    extraction_diagnostics: dict
    data_provider: Literal["fixture", "akshare"]
    cache_enabled: bool
    fallback_to_fixture: bool
    market_data_cache_dir: str
    market_data_diagnostics: dict
    source_diagnostics: dict
    backtest_assumptions: dict
    audit_trail: list[dict]
    sources: list[dict]
    discovered_sources: list[dict]
    chunks: list[dict]
    hypotheses: list[dict]
    factor_specs: list[dict]
    validation_results: list[dict]
    market_data_summary: dict
    metrics: list[dict]
    backtest_series: dict
    report_markdown: str
    selected_factors: list[str]
    warnings: list[str]
    errors: list[dict]
    trace: list[dict]
    event_db_path: str
    _market_data: Any
    _factor_values: dict[str, Any]
    _oos_split_date: str
    _factor_correlation: dict[str, Any]
    oos_metrics: list[dict]
