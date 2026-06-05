import json
from dataclasses import dataclass
from typing import Protocol

from app.agents.nodes import extract_hypotheses_from_chunks
from app.agents.prompts import FACTOR_EXTRACTION_PROMPT
from app.agents.schemas import FactorHypothesis
from app.rag.chunker import DocumentChunk


class TextLlmClient(Protocol):
    def text(self, prompt: str) -> str:
        pass


@dataclass(frozen=True)
class StructuredExtractionResult:
    hypotheses: list[FactorHypothesis]
    diagnostics: dict


def parse_factor_extraction_response(text: str) -> list[FactorHypothesis]:
    data = json.loads(_strip_json_markdown(text))
    return [FactorHypothesis(**item) for item in data.get("factors", [])]


class StructuredFactorExtractor:
    def __init__(self, llm_client: TextLlmClient | None = None) -> None:
        self.llm_client = llm_client

    def extract(
        self,
        research_topic: str,
        chunks: list[DocumentChunk],
        extraction_mode: str = "hybrid",
        enable_llm_extraction: bool = False,
        llm_retry_count: int = 1,
    ) -> StructuredExtractionResult:
        normalized_mode = extraction_mode if extraction_mode in {"rule", "llm", "hybrid"} else "hybrid"
        diagnostics = {
            "extraction_mode": normalized_mode,
            "llm_attempted": False,
            "fallback_used": False,
            "fallback_reason": None,
            "hypothesis_count": 0,
        }

        should_try_llm = normalized_mode == "llm" or (
            normalized_mode == "hybrid" and enable_llm_extraction
        )
        if should_try_llm:
            llm_result = self._try_llm_extract(research_topic, chunks, llm_retry_count)
            diagnostics.update(llm_result.diagnostics)
            if llm_result.hypotheses:
                diagnostics["hypothesis_count"] = len(llm_result.hypotheses)
                return StructuredExtractionResult(llm_result.hypotheses, diagnostics)

        hypotheses = extract_hypotheses_from_chunks(research_topic, chunks)
        diagnostics["fallback_used"] = should_try_llm
        if should_try_llm and not diagnostics.get("fallback_reason"):
            diagnostics["fallback_reason"] = "llm_returned_no_hypotheses"
        diagnostics["hypothesis_count"] = len(hypotheses)
        return StructuredExtractionResult(hypotheses, diagnostics)

    def _try_llm_extract(
        self,
        research_topic: str,
        chunks: list[DocumentChunk],
        llm_retry_count: int,
    ) -> StructuredExtractionResult:
        diagnostics = {
            "llm_attempted": True,
            "llm_error": None,
            "llm_retry_count": 0,
            "fallback_reason": None,
        }
        if self.llm_client is None:
            try:
                from app.llm.client import LlmClient

                self.llm_client = LlmClient()
            except Exception as exc:
                diagnostics["fallback_reason"] = "llm_client_unavailable"
                diagnostics["llm_error"] = str(exc)
                return StructuredExtractionResult([], diagnostics)

        prompt = FACTOR_EXTRACTION_PROMPT.format(
            research_topic=research_topic,
            chunks=_render_chunks(chunks),
        )
        attempts = max(1, llm_retry_count + 1)
        last_error = None
        response_text = ""
        for attempt in range(attempts):
            try:
                if attempt == 0:
                    response_text = self.llm_client.text(prompt)
                else:
                    diagnostics["llm_retry_count"] += 1
                    response_text = self.llm_client.text(_repair_prompt(response_text, str(last_error)))
                hypotheses = parse_factor_extraction_response(response_text)
                if hypotheses:
                    return StructuredExtractionResult(hypotheses, diagnostics)
                last_error = ValueError("empty_factors")
            except Exception as exc:
                last_error = exc
        diagnostics["fallback_reason"] = "llm_invalid_output"
        diagnostics["llm_error"] = str(last_error)
        return StructuredExtractionResult([], diagnostics)


def _strip_json_markdown(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        return "\n".join(lines).strip()
    return stripped


def _render_chunks(chunks: list[DocumentChunk]) -> str:
    items = []
    for chunk in chunks[:8]:
        items.append(
            {
                "chunk_id": chunk.chunk_id,
                "source_title": chunk.source_title,
                "source_url": chunk.source_url,
                "text": chunk.text[:1200],
            }
        )
    return json.dumps(items, ensure_ascii=False, indent=2)


def _repair_prompt(previous_response: str, error: str) -> str:
    return (
        "Repair the following factor extraction response into valid JSON only. "
        "The JSON must have a top-level factors list and each factor must include "
        "factor_name, hypothesis, evidence, source_title, source_url, category, "
        "required_fields, and confidence.\n\n"
        f"Validation error:\n{error}\n\n"
        f"Previous response:\n{previous_response}"
    )
