import asyncio
import time
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from google import genai

from app import intelligence, repository
from app.config import settings
from app.main import app


def install_fake_client(monkeypatch, behaviour):
    """Replace genai.Client with a fake whose async generate_content runs `behaviour`."""
    class FakeModels:
        async def generate_content(self, model, contents):
            return await behaviour()
        def generate_content_sync(self, *args, **kwargs):
            time.sleep(1)  # A blocking call; must never be used.

    class FakeClient:
        def __init__(self, api_key):
            assert api_key == "test-key"
            self.aio = SimpleNamespace(models=FakeModels())
            self.models = SimpleNamespace(generate_content=FakeModels().generate_content_sync)

    monkeypatch.setattr(genai, "Client", FakeClient)
    monkeypatch.setattr(settings, "gemini_api_key", "test-key")


def run(coro):
    return asyncio.run(coro)


def test_not_configured_reports_reason(monkeypatch):
    monkeypatch.setattr(settings, "gemini_api_key", "")
    result = run(intelligence.analyze_context("ctx"))
    assert result.ai_used is False and result.ai_error == "not_configured"
    assert "not configured" in result.summary


def test_success_sets_ai_used_without_error(monkeypatch):
    async def ok():
        return SimpleNamespace(text="Summary line\nObservation A\nObservation B")
    install_fake_client(monkeypatch, ok)
    result = run(intelligence.analyze_context("ctx", "Partner"))
    assert result.ai_used is True and result.ai_error is None
    assert result.summary == "Summary line" and result.observations == ["Observation A", "Observation B"]


def test_timeout_is_reported(monkeypatch):
    async def slow():
        await asyncio.sleep(1)
    install_fake_client(monkeypatch, slow)
    monkeypatch.setattr(settings, "gemini_timeout_seconds", 0.05)
    result = run(intelligence.analyze_context("ctx"))
    assert result.ai_used is False and result.ai_error == "timeout"
    assert "0.05 seconds" in result.summary


def test_api_error_code_is_reported(monkeypatch):
    class QuotaError(Exception):
        code = 429
    async def fail():
        raise QuotaError("quota exceeded for key test-key")
    install_fake_client(monkeypatch, fail)
    result = run(intelligence.analyze_context("ctx"))
    assert result.ai_used is False and result.ai_error == "api_error:429"
    assert "test-key" not in result.summary


def test_other_error_type_is_reported(monkeypatch):
    async def fail():
        raise ConnectionError("network down")
    install_fake_client(monkeypatch, fail)
    assert run(intelligence.analyze_context("ctx")).ai_error == "error:ConnectionError"


def test_empty_response_is_reported(monkeypatch):
    async def empty():
        return SimpleNamespace(text="   ")
    install_fake_client(monkeypatch, empty)
    result = run(intelligence.analyze_context("ctx"))
    assert result.ai_used is False and result.ai_error == "empty_response"


def test_concurrent_requests_do_not_block_each_other(monkeypatch):
    async def slow_ok():
        await asyncio.sleep(0.3)
        return SimpleNamespace(text="Summary")
    install_fake_client(monkeypatch, slow_ok)
    async def three():
        return await asyncio.gather(*(intelligence.analyze_context("ctx") for _ in range(3)))
    started = time.perf_counter()
    results = run(three())
    assert all(r.ai_used for r in results)
    assert time.perf_counter() - started < 0.8  # Serialized calls would take at least 0.9 s.


def test_route_exposes_ai_error(monkeypatch):
    repository._firestore_client = None
    repository._firestore_attempted = True
    monkeypatch.setattr(settings, "gemini_api_key", "")
    response = TestClient(app).post("/api/intelligence/analyze", json={"partner_id": "demo-001"})
    assert response.status_code == 200
    body = response.json()
    assert body["ai_used"] is False and body["ai_error"] == "not_configured"
