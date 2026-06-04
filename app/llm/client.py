import json
from typing import Any

from app.config import get_settings


class LlmClient:
    def __init__(self) -> None:
        self.settings = get_settings()

    def text(self, prompt: str) -> str:
        if not self.settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured; use deterministic fallback.")
        from openai import OpenAI

        response = OpenAI(api_key=self.settings.openai_api_key).responses.create(
            model=self.settings.llm_model,
            input=prompt,
        )
        return response.output_text

    def json(self, prompt: str) -> dict[str, Any]:
        return json.loads(self.text(prompt))

