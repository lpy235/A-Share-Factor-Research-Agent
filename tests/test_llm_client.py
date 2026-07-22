import sys
from types import SimpleNamespace

from app.llm.client import LlmClient


def test_llm_client_uses_runtime_model_key_and_base_url(monkeypatch):
    captured = {}

    class FakeResponses:
        def create(self, *, model, input):
            captured["model"] = model
            captured["input"] = input
            return SimpleNamespace(output_text="ok")

    class FakeOpenAI:
        def __init__(self, *, api_key, base_url):
            captured["api_key"] = api_key
            captured["base_url"] = base_url
            self.responses = FakeResponses()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=FakeOpenAI))
    client = LlmClient(
        provider="custom",
        api_key="sk-runtime",
        base_url="https://llm.example.com/v1",
        model="custom-model",
    )

    assert client.text("prompt") == "ok"
    assert captured == {
        "api_key": "sk-runtime",
        "base_url": "https://llm.example.com/v1",
        "model": "custom-model",
        "input": "prompt",
    }
