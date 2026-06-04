import math

from app.agents.nodes import extract_hypotheses_from_chunks, generate_factor_specs
from app.agents.state import ResearchState
from app.backtest.metrics import max_drawdown, sharpe_ratio
from app.backtest.selector import FactorScore, FactorSelector
from app.backtest.single_factor import (
    compute_forward_returns,
    compute_rank_ic,
    grouped_forward_returns,
)
from app.data.fixture_provider import FixtureAshareDataProvider
from app.factor.executor import FactorExecutor
from app.rag.chunker import DocumentChunk
from app.rag.chunker import SimpleChunker
from app.rag.retriever import KeywordRetriever
from app.reports.markdown_report import render_report
from app.sources.parser import DocumentParser


def _safe_float(value: float) -> float:
    if value is None or math.isnan(value) or math.isinf(value):
        return 0.0
    return float(value)


def run_research_workflow(state: ResearchState) -> ResearchState:
    chunks = _load_research_chunks(state)

    hypotheses = extract_hypotheses_from_chunks(state["research_topic"], chunks)
    if not hypotheses:
        fallback = DocumentChunk(
            chunk_id="fallback:0",
            source_title="fallback factor note",
            source_type="fallback",
            text="成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。",
        )
        chunks = [fallback]
        hypotheses = extract_hypotheses_from_chunks(state["research_topic"], chunks)
    specs = generate_factor_specs(hypotheses)

    provider = FixtureAshareDataProvider()
    symbols = provider.get_universe(state.get("universe", "CSI300"), state.get("start_date", "2020-01-01"))[:20]
    data = provider.get_daily_bars(
        symbols=symbols,
        start_date=state.get("start_date", "2020-01-01"),
        end_date=state.get("end_date", "2020-12-31"),
    )

    executor = FactorExecutor()
    metrics = []
    selected_input = []
    for spec in specs:
        factor = executor.execute(spec, data).values
        forward_returns = compute_forward_returns(data["close"], periods=1)
        rank_ic = compute_rank_ic(factor, forward_returns)
        grouped = grouped_forward_returns(factor, forward_returns, groups=5)
        long_short = grouped[5] - grouped[1] if {1, 5}.issubset(grouped.columns) else grouped.mean(axis=1) * 0
        rank_ic_std = rank_ic.std()
        score = {
            "factor_name": spec.factor_name,
            "mean_rank_ic": round(_safe_float(rank_ic.mean()), 6),
            "icir": round(_safe_float(rank_ic.mean() / rank_ic_std) if rank_ic_std else 0.0, 6),
            "coverage_ratio": round(float(factor.notna().mean()), 6),
            "missing_ratio": round(float(factor.isna().mean()), 6),
            "max_drawdown": round(max_drawdown(long_short), 6),
            "sharpe": round(sharpe_ratio(long_short), 6),
        }
        metrics.append(score)
        selected_input.append(
            FactorScore(
                factor_name=score["factor_name"],
                mean_rank_ic=score["mean_rank_ic"],
                icir=score["icir"],
                coverage_ratio=score["coverage_ratio"],
                missing_ratio=score["missing_ratio"],
                max_drawdown=score["max_drawdown"],
            )
        )

    selected = FactorSelector(
        min_abs_rank_ic=0.0,
        min_abs_icir=0.0,
        min_coverage=0.7,
        max_missing=0.3,
    ).select(selected_input)
    report = render_report(
        research_topic=state["research_topic"],
        sources=[{"source_title": h.source_title, "source_url": h.source_url} for h in hypotheses],
        factors=[spec.model_dump() for spec in specs],
        metrics=metrics,
        limitations=[
            "当前第一版使用 fixture 数据演示完整流程。",
            "正式研究需要替换为 AKShare/Tushare 等合法 A 股数据源。",
            "历史回测不构成投资建议。",
        ],
    )
    state["factor_specs"] = [spec.model_dump() for spec in specs]
    state["metrics"] = metrics
    state["report_markdown"] = report
    state["selected_factors"] = [item.factor_name for item in selected]
    return state


def _load_research_chunks(state: ResearchState) -> list[DocumentChunk]:
    document_paths = state.get("document_paths", [])
    if not document_paths:
        return [
            DocumentChunk(
                chunk_id="demo:0",
                source_title="demo factor note",
                source_type="user_upload",
                text="成交量放大且价格上涨，可能代表趋势延续，可构造量价动量因子。过去收益率较高的股票也可能体现动量效应。",
            )
        ]

    parser = DocumentParser()
    chunker = SimpleChunker()
    chunks: list[DocumentChunk] = []
    for path in document_paths:
        parsed = parser.parse_file(path)
        chunks.extend(
            chunker.chunk(parsed.source_title, parsed.source_type, parsed.text, parsed.source_url)
        )
    if not chunks:
        return []
    retriever = KeywordRetriever(chunks)
    retrieved = retriever.search(state["research_topic"], top_k=state.get("max_chunks", 5))
    return retrieved or chunks[: state.get("max_chunks", 5)]
