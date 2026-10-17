import asyncio
import time

import pytest
from fastapi.testclient import TestClient
import httpx

from app import intelligence, repository
from app.config import settings
from app.main import app


def install_fake_client(monkeypatch, behaviour):
    class FakeResponse:
        def __init__(self, status_code=200, content="Summary line\nObservation A\nObservation B"):
            self.status_code = status_code
            self.content = content

        def raise_for_status(self):
            if self.status_code >= 400:
                request = httpx.Request("POST", intelligence.GROQ_CHAT_COMPLETIONS_URL)
                response = httpx.Response(self.status_code, request=request)
                raise httpx.HTTPStatusError("request failed", request=request, response=response)

        def json(self):
            return {"choices": [{"message": {"content": self.content}}]}

    class FakeClient:
        def __init__(self, timeout):
            self.timeout = timeout

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return None

        async def post(self, url, headers, json):
            assert url == intelligence.GROQ_CHAT_COMPLETIONS_URL
            assert headers["Authorization"].startswith("Bearer ")
            assert json["model"] == "test-model"
            assert json["messages"][0]["role"] == "user"
            return await behaviour(FakeResponse)

    monkeypatch.setattr(intelligence.httpx, "AsyncClient", FakeClient)
    monkeypatch.setattr(settings, "groq_api_key", "test-key")
    monkeypatch.setattr(settings, "groq_model", "test-model")


def run(coro):
    return asyncio.run(coro)


def test_not_configured_reports_reason(monkeypatch):
    monkeypatch.setattr(settings, "groq_api_key", "")
    result = run(intelligence.analyze_context("ctx"))
    assert result.ai_used is False and result.ai_error == "not_configured"
    assert "Groq is not configured" in result.summary


def test_success_uses_groq_and_parses_text(monkeypatch):
    async def ok(response):
        return response()

    install_fake_client(monkeypatch, ok)
    result = run(intelligence.analyze_context("ctx", "Fictional Partner"))
    assert result.ai_used is True and result.ai_error is None
    assert result.summary == "Summary line"
    assert result.observations == ["Observation A", "Observation B"]


def test_timeout_is_reported(monkeypatch):
    async def slow(response):
        await asyncio.sleep(1)
        return response()

    install_fake_client(monkeypatch, slow)
    monkeypatch.setattr(settings, "groq_timeout_seconds", 0.05)
    result = run(intelligence.analyze_context("ctx"))
    assert result.ai_used is False and result.ai_error == "timeout"
    assert "0.05 seconds" in result.summary


def test_http_error_code_is_reported_without_secret(monkeypatch):
    async def fail(response):
        return response(status_code=429, content="test-key")

    install_fake_client(monkeypatch, fail)
    result = run(intelligence.analyze_context("ctx"))
    assert result.ai_used is False and result.ai_error == "api_error:429"
    assert "test-key" not in result.summary


def test_other_error_type_is_reported(monkeypatch):
    async def fail(response):
        raise ConnectionError("network down")

    install_fake_client(monkeypatch, fail)
    assert run(intelligence.analyze_context("ctx")).ai_error == "error:ConnectionError"


def test_empty_response_is_reported(monkeypatch):
    async def empty(response):
        return response(content="   ")

    install_fake_client(monkeypatch, empty)
    result = run(intelligence.analyze_context("ctx"))
    assert result.ai_used is False and result.ai_error == "empty_response"


def test_concurrent_requests_do_not_block_each_other(monkeypatch):
    async def slow_ok(response):
        await asyncio.sleep(0.3)
        return response(content="Summary")

    install_fake_client(monkeypatch, slow_ok)

    async def three():
        return await asyncio.gather(*(intelligence.analyze_context("ctx") for _ in range(3)))

    started = time.perf_counter()
    results = run(three())
    assert all(result.ai_used for result in results)
    assert time.perf_counter() - started < 0.8


def test_route_exposes_ai_error(monkeypatch):
    repository._firestore_client = None
    repository._firestore_attempted = True
    monkeypatch.setattr(settings, "groq_api_key", "")
    response = TestClient(app).post("/api/intelligence/analyze", json={"partner_id": "demo-001"})
    assert response.status_code == 200
    body = response.json()
    assert body["ai_used"] is False and body["ai_error"] == "not_configured"
