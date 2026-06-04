from collections.abc import Callable
from typing import Any

from app.agents.state import ResearchState
from app.storage.db import init_db
from app.storage.events import EventStore


Payload = dict[str, Any]
NodeWork = Callable[[ResearchState, "GraphEventTracer"], ResearchState]
SummaryBuilder = Callable[[ResearchState], Payload]


class GraphEventTracer:
    def __init__(self, state: ResearchState) -> None:
        self.run_id = state.get("run_id")
        db_path = state.get("event_db_path")
        self.store = None
        if self.run_id and db_path:
            init_db(db_path)
            self.store = EventStore(db_path)
        state.setdefault("trace", [])
        self.state = state

    def node_started(self, node: str, payload: Payload) -> None:
        self._append(node, "node_started", payload)

    def node_completed(self, node: str, payload: Payload) -> None:
        self._append(node, "node_completed", payload)

    def node_fallback(self, node: str, payload: Payload) -> None:
        self._append(node, "node_fallback", payload)

    def node_failed(self, node: str, payload: Payload) -> None:
        self._append(node, "node_failed", payload)

    def _append(self, node: str, event_type: str, payload: Payload) -> None:
        compact_payload = _compact(payload)
        event = {"node": node, "event_type": event_type, "payload": compact_payload}
        self.state.setdefault("trace", []).append(event)
        if self.run_id and self.store:
            self.store.append(self.run_id, node, event_type, compact_payload)


def run_traced_node(
    state: ResearchState,
    node_name: str,
    work: NodeWork,
    input_summary: SummaryBuilder,
    output_summary: SummaryBuilder,
) -> ResearchState:
    tracer = GraphEventTracer(state)
    tracer.node_started(node_name, {"input_summary": input_summary(state)})
    try:
        next_state = work(state, tracer)
    except Exception as exc:
        error = {"node": node_name, "message": str(exc)}
        state.setdefault("errors", []).append(error)
        tracer.node_failed(node_name, {"error": error})
        raise
    tracer.node_completed(
        node_name,
        {
            "output_summary": output_summary(next_state),
            "warnings": next_state.get("warnings", []),
        },
    )
    return next_state


def _compact(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _compact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_compact(item) for item in value[:20]]
    if isinstance(value, tuple):
        return [_compact(item) for item in value[:20]]
    if isinstance(value, (str, int, float, bool)) or value is None:
        if isinstance(value, str) and len(value) > 240:
            return value[:237] + "..."
        return value
    return str(value)
