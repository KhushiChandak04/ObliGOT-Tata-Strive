"""Small server-side client for Groq chat completions."""
import asyncio
import base64
import json
import logging
import random
from typing import Any

import httpx

from app.config import settings
from pydantic import BaseModel

logger = logging.getLogger("obligot.groq")
GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
_semaphores: dict[int, asyncio.Semaphore] = {}


class GroqRequestError(RuntimeError):
    def __init__(self, code: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.code = code
        self.retryable = retryable


def image_data_url(image: bytes, mime_type: str = "image/jpeg") -> str:
    encoded = base64.b64encode(image).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _limit() -> asyncio.Semaphore:
    loop_id = id(asyncio.get_running_loop())
    if loop_id not in _semaphores:
        _semaphores[loop_id] = asyncio.Semaphore(max(1, settings.groq_max_concurrency))
    return _semaphores[loop_id]


def _error(status_code: int, body: str = "") -> GroqRequestError:
    if status_code == 400 and "json_validate_failed" in body:
        # The model produced invalid JSON this time; another attempt usually succeeds.
        return GroqRequestError("invalid_json", "Groq returned invalid JSON", retryable=True)
    if status_code == 413:
        return GroqRequestError("too_large", "The request is larger than the Groq token-per-minute limit (lower EXTRACTION_CHUNK_CHARS)")
    if status_code in (401, 403):
        return GroqRequestError("auth_error", "Groq rejected the API key (check GROQ_API_KEY)")
    if status_code == 404:
        return GroqRequestError("model_not_found", "The configured Groq model is not available to this key")
    if status_code == 429:
        return GroqRequestError("rate_limited", "Groq rate limit reached", retryable=True)
    if status_code >= 500:
        return GroqRequestError("unavailable", "Groq is temporarily unavailable", retryable=True)
    return GroqRequestError("invalid_request", "Groq rejected the extraction request")


async def chat_completion(
    messages: list[dict[str, Any]],
    *,
    model: str,
    timeout: float,
    response_format: dict[str, str] | None = None,
    max_completion_tokens: int | None = None,
) -> str:
    if not settings.groq_api_key:
        raise GroqRequestError("not_configured", "Groq is not configured on the server")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0,
    }
    if response_format:
        payload["response_format"] = response_format
    if max_completion_tokens:
        payload["max_completion_tokens"] = max_completion_tokens

    for attempt in range(settings.groq_max_retries + 1):
        try:
            async with _limit():
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await asyncio.wait_for(
                        client.post(
                            GROQ_CHAT_COMPLETIONS_URL,
                            headers={"Authorization": f"Bearer {settings.groq_api_key}"},
                            json=payload,
                        ),
                        timeout=timeout,
                    )
            if response.status_code >= 400:
                detail = str(getattr(response, "text", "") or "")
                error = _error(response.status_code, detail)
                logger.warning("Groq HTTP %s on %s: %s", response.status_code, model, detail[:300])
                if not error.retryable or attempt >= settings.groq_max_retries:
                    raise error
                retry_after = response.headers.get("retry-after")
                try:
                    delay = float(retry_after) if retry_after else settings.groq_backoff_base_seconds * (2 ** attempt)
                except ValueError:
                    delay = settings.groq_backoff_base_seconds * (2 ** attempt)
            else:
                body = response.json()
                choices = body.get("choices") or []
                message = choices[0].get("message") if choices else {}
                content = message.get("content") if isinstance(message, dict) else None
                generated = content.strip() if isinstance(content, str) else ""
                if not generated:
                    raise GroqRequestError("empty_response", "Groq returned an empty response")
                return generated
        except (asyncio.TimeoutError, httpx.TimeoutException) as exc:
            if attempt >= settings.groq_max_retries:
                raise GroqRequestError("timeout", "Groq did not respond in time", retryable=True) from exc
            delay = settings.groq_backoff_base_seconds * (2 ** attempt)
        except httpx.RequestError as exc:
            if attempt >= settings.groq_max_retries:
                raise GroqRequestError(f"error:{type(exc).__name__}", "Could not reach Groq", retryable=True) from exc
            delay = settings.groq_backoff_base_seconds * (2 ** attempt)
        except GroqRequestError:
            raise
        except Exception as exc:
            raise GroqRequestError(f"error:{type(exc).__name__}", "Groq returned an invalid response") from exc

        delay = min(max(0.0, delay), settings.groq_max_retry_wait_seconds)
        logger.warning("Groq request retrying after a transient failure (attempt %s)", attempt + 1)
        await asyncio.sleep(delay + random.uniform(0, min(0.25, delay * 0.25)))

    raise GroqRequestError("unavailable", "Groq request did not complete", retryable=True)


async def structured_completion(
    messages: list[dict[str, Any]],
    schema: type[BaseModel],
    *,
    model: str,
    timeout: float,
) -> str:
    schema_message = {
        "role": "system",
        "content": (
            "Return only a valid JSON object matching this JSON schema. Do not add markdown or prose:\n"
            + json.dumps(schema.model_json_schema(), ensure_ascii=False)
        ),
    }
    return await chat_completion(
        [schema_message, *messages],
        model=model,
        timeout=timeout,
        response_format={"type": "json_object"},
        max_completion_tokens=8192,
    )
