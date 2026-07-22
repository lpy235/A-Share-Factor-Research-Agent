import json
from typing import Any

from app.config import get_settings


class LlmClient:
    def __init__(
        self,
        *,
        provider: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
    ) -> None:
        self.settings = get_settings()
        self.provider = provider or "openai"
        self.api_key = api_key if api_key is not None else self.settings.openai_api_key
        self.base_url = base_url or None
        self.model = model or self.settings.llm_model

    def text(self, prompt: str) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured; use deterministic fallback.")
        from openai import OpenAI

        response = OpenAI(api_key=self.api_key, base_url=self.base_url).responses.create(
            model=self.model,
            input=prompt,
        )
        return response.output_text

    def json(self, prompt: str) -> dict[str, Any]:
        return json.loads(self.text(prompt))
