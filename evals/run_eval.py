import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.agents.nodes import extract_hypotheses_from_chunks
from app.factor.dsl import FactorSpec
from app.factor.validator import FactorDslValidator
from app.rag.chunker import DocumentChunk


def run() -> None:
    path = Path(__file__).with_name("tasks.jsonl")
    tasks = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    validator = FactorDslValidator()
    total = 0
    correct = 0

    for task in tasks:
        if task["type"] == "dsl_validation":
            spec = FactorSpec(
                factor_name=task["id"],
                hypothesis="eval",
                formula=task["formula"],
                required_fields=["close"],
                direction="unknown",
                category="eval",
                frequency="daily",
                lookback=20,
                source_title="eval",
                source_url=None,
                source_excerpt="eval",
                confidence=0.5,
            )
            result = validator.validate(spec)
            total += 1
            correct += int(result.valid == task["expected_valid"])
        elif task["type"] == "factor_extraction":
            chunk = DocumentChunk(task["id"], "eval", "user_upload", task["text"])
            hypotheses = extract_hypotheses_from_chunks("A股因子", [chunk])
            total += 1
            if hypotheses:
                first = hypotheses[0]
                fields_ok = set(first.required_fields) == set(task["expected_fields"])
                category_ok = first.category == task["expected_category"]
                correct += int(fields_ok and category_ok)

    print({"total": total, "correct": correct, "accuracy": correct / total if total else 0})


if __name__ == "__main__":
    run()
