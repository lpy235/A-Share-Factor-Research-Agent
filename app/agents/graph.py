from langgraph.graph import END, START, StateGraph

from app.agents.graph_nodes import (
    execute_factors_node,
    extract_hypotheses_node,
    generate_factor_dsl_node,
    generate_report_node,
    load_documents_node,
    load_market_data_node,
    retrieve_chunks_node,
    run_backtest_node,
    select_factors_node,
    validate_dsl_node,
)
from app.agents.state import ResearchState


NODE_ORDER = [
    ("LoadDocumentsNode", load_documents_node),
    ("RetrieveChunksNode", retrieve_chunks_node),
    ("ExtractHypothesesNode", extract_hypotheses_node),
    ("GenerateFactorDSLNode", generate_factor_dsl_node),
    ("ValidateDSLNode", validate_dsl_node),
    ("LoadMarketDataNode", load_market_data_node),
    ("ExecuteFactorsNode", execute_factors_node),
    ("RunBacktestNode", run_backtest_node),
    ("SelectFactorsNode", select_factors_node),
    ("GenerateReportNode", generate_report_node),
]


def build_research_graph():
    graph = StateGraph(ResearchState)
    for node_name, node_func in NODE_ORDER:
        graph.add_node(node_name, node_func)

    graph.add_edge(START, NODE_ORDER[0][0])
    for (current_name, _), (next_name, _) in zip(NODE_ORDER[:-1], NODE_ORDER[1:], strict=True):
        graph.add_edge(current_name, next_name)
    graph.add_edge(NODE_ORDER[-1][0], END)
    return graph.compile()


def run_research_workflow(state: ResearchState) -> ResearchState:
    if not state.get("run_id"):
        raise ValueError("run_id is required")
    if not state.get("research_topic"):
        raise ValueError("research_topic is required")

    initial_state: ResearchState = {
        "source_mode": "upload",
        "universe": "CSI300",
        "start_date": "2020-01-01",
        "end_date": "2020-12-31",
        "max_chunks": 5,
        "max_sources": 3,
        "allow_live_fetch": False,
        "warnings": [],
        "errors": [],
        "trace": [],
        **state,
    }
    result = build_research_graph().invoke(initial_state)
    return result
