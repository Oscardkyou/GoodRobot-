"""Tests for local DistilGPT-2 integration in app.ai_agent.simple_ai.

We provide two categories of tests:
- fast unit tests that mock HF pipeline (no network, no model download)
- optional integration tests that run the real model (requires ~300-500MB download)

To run integration tests set env var RUN_LLM_TESTS=1, e.g.:
    RUN_LLM_TESTS=1 pytest -q tests/test_ai_local.py::test_integration_generate_simple
"""
from __future__ import annotations

import os
from typing import Any, Dict, List

import pytest

from app.ai_agent.simple_ai import GeminiAI, get_ai_response


class _DummyTokenizer:
    eos_token_id = 50256  # GPT-2 default


class _DummyPipe:
    def __init__(self, tokenizer: _DummyTokenizer | None = None):
        self.tokenizer = tokenizer or _DummyTokenizer()
        self._calls: int = 0

    def __call__(self, prompt: str, **kwargs: Any) -> List[Dict[str, str]]:
        # record generation call
        self._calls += 1
        # Simulate generation by appending a short answer
        return [{"generated_text": f"{prompt} Это краткий ответ модели."}]


def test_get_ai_response_uses_local_pipeline(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_ai_response should use local pipeline and return non-empty short result.

    We monkeypatch the pipeline factory inside simple_ai to avoid network/model load.
    """
    import app.ai_agent.simple_ai as simple_ai

    created: dict = {"count": 0}

    def _fake_pipeline(task: str, model=None, tokenizer=None, device=-1):
        # validate expected args
        assert task == "text-generation"
        assert device == -1  # CPU
        created["count"] += 1
        return _DummyPipe(tokenizer=_DummyTokenizer())

    # Patch only within our module to keep scope narrow
    monkeypatch.setattr(simple_ai, "pipeline", _fake_pipeline)

    # Now call public helper
    answer = get_ai_response("Как выбрать мастера для ремонта?")

    assert isinstance(answer, str)
    assert len(answer) > 0
    # Should not be overly long (the implementation trims to 200 chars)
    assert len(answer) <= 205
    # Pipeline is lazily created exactly once
    assert created["count"] == 1


def test_initialize_idempotent(monkeypatch: pytest.MonkeyPatch) -> None:
    """initialize() must be safe to call multiple times without re-creating pipeline."""
    import app.ai_agent.simple_ai as simple_ai

    created: dict = {"count": 0}
    dummy_pipe = _DummyPipe()

    def _fake_pipeline(task: str, model=None, tokenizer=None, device=-1):
        created["count"] += 1
        return dummy_pipe

    monkeypatch.setattr(simple_ai, "pipeline", _fake_pipeline)

    ai = GeminiAI()
    ai.initialize()
    ai.initialize()  # call twice

    assert created["count"] == 1  # created once
    # and calls go through the same dummy pipe
    res = ai.get_response("Привет!")
    assert isinstance(res, str) and len(res) > 0
    assert dummy_pipe._calls == 1


@pytest.mark.skipif(os.getenv("RUN_LLM_TESTS") != "1", reason="Set RUN_LLM_TESTS=1 to run integration tests")
def test_integration_generate_simple() -> None:
    """Integration test that runs the real DistilGPT-2 model on CPU.

    Requires network on first run to download weights from the Hugging Face Hub.
    Subsequent runs use local cache (~/.cache/huggingface by default).
    """
    ai = GeminiAI()
    ai.initialize()

    text = ai.get_response("Скажи одно короткое предложение о погоде.")
    assert isinstance(text, str)
    assert 0 < len(text) <= 220


@pytest.mark.skipif(os.getenv("RUN_LLM_TESTS") != "1", reason="Set RUN_LLM_TESTS=1 to run integration tests")
def test_integration_get_ai_response() -> None:
    resp = get_ai_response("Как оформить заказ у мастера?")
    assert isinstance(resp, str)
    assert 0 < len(resp) <= 220
