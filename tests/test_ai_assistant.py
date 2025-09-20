import re
import pytest

from app.ai_agent.simple_ai import GeminiAI, get_ai_response


@pytest.fixture(autouse=True)
def _no_model_init(monkeypatch):
    """Prevent heavy model initialization during tests."""
    monkeypatch.setattr(GeminiAI, "initialize", lambda self: None)


def test_short_or_unclear_input_returns_clarifying_message():
    resp = get_ai_response("Что?")
    assert "Чем могу помочь?" in resp
    assert "опишите задачу" in resp.lower()


def test_repetitions_are_sanitized(monkeypatch):
    # Force model to return a repetitive low-quality output
    monkeypatch.setattr(GeminiAI, "get_response", lambda self, prompt: "Ответ: Что? Что? Что? Что? Что?")
    resp = get_ai_response("Расскажи про сервис")
    # After sanitization, response should not contain many repeated 'Что?'
    occ = len(re.findall(r"Что\?", resp))
    assert occ <= 2
    assert len(resp.strip()) > 0


def test_normal_question_returns_short_answer(monkeypatch):
    monkeypatch.setattr(GeminiAI, "get_response", lambda self, prompt: "Мы поможем оформить заявку и выбрать мастера в пару шагов.")
    resp = get_ai_response("Как работает сервис?")
    assert len(resp) <= 220
    assert "заяв" in resp.lower() or "мастер" in resp.lower()
