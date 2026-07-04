"""
NVIDIA NIM LLM client — OpenAI-compatible interface.
Handles retries, timeouts, streaming, and structured JSON outputs.
"""
from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncIterator

import httpx
from openai import AsyncOpenAI, APITimeoutError, APIConnectionError, RateLimitError as OpenAIRateLimitError

from app.core.config import get_settings
from app.core.exceptions import LLMError, LLMTimeoutError
from app.core.logging import get_logger

logger = get_logger(__name__)


def _build_client() -> AsyncOpenAI:
    settings = get_settings()
    return AsyncOpenAI(
        api_key=settings.nvidia_api_key,
        base_url=settings.nvidia_base_url,
        timeout=httpx.Timeout(
            connect=10.0,
            read=settings.llm_timeout_seconds,
            write=10.0,
            pool=5.0,
        ),
        max_retries=0,  # We implement our own retry logic
    )


class LLMClient:
    """
    Thin wrapper over the NVIDIA NIM OpenAI-compatible API.

    Responsibilities:
    - Retry with exponential backoff
    - Streaming token-by-token yields
    - Structured JSON output parsing
    - Centralized error mapping
    """

    def __init__(self) -> None:
        self._client = _build_client()
        self._settings = get_settings()

    async def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        json_mode: bool = False,
        model: str | None = None,
    ) -> str:
        """
        Non-streaming completion. Returns the full response text.
        Retries up to llm_max_retries times with exponential backoff.
        """
        model = model or self._settings.nvidia_model
        max_tokens = max_tokens or self._settings.llm_max_tokens
        temperature = temperature if temperature is not None else self._settings.llm_temperature

        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        last_error: Exception | None = None
        for attempt in range(1, self._settings.llm_max_retries + 1):
            try:
                logger.info(
                    "llm_request",
                    model=model,
                    attempt=attempt,
                    json_mode=json_mode,
                    messages_count=len(messages),
                )
                response = await self._client.chat.completions.create(**kwargs)
                content = response.choices[0].message.content or ""
                logger.info("llm_response_ok", tokens=response.usage.total_tokens if response.usage else None)
                return content

            except APITimeoutError as exc:
                last_error = exc
                logger.warning("llm_timeout", attempt=attempt)
                if attempt < self._settings.llm_max_retries:
                    await asyncio.sleep(2 ** attempt)

            except APIConnectionError as exc:
                last_error = exc
                logger.warning("llm_connection_error", attempt=attempt, error=str(exc))
                if attempt < self._settings.llm_max_retries:
                    await asyncio.sleep(2 ** attempt)

            except OpenAIRateLimitError as exc:
                last_error = exc
                logger.warning("llm_rate_limited", attempt=attempt)
                await asyncio.sleep(5 * attempt)

            except Exception as exc:
                logger.error("llm_unexpected_error", error=str(exc))
                raise LLMError(f"Unexpected LLM error: {exc}") from exc

        if isinstance(last_error, APITimeoutError):
            raise LLMTimeoutError("LLM request timed out after all retries.")
        raise LLMError(f"LLM request failed after {self._settings.llm_max_retries} retries: {last_error}")

    async def complete_json(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
    ) -> dict[str, Any]:
        """Complete and parse response as JSON. Raises LLMError on parse failure."""
        raw = await self.complete(
            messages,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=True,
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            # Attempt to extract JSON block from markdown code fences
            import re
            match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", raw, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(1))
                except json.JSONDecodeError:
                    pass
            raise LLMError(f"Failed to parse LLM JSON response: {exc}\nRaw: {raw[:200]}") from exc

    async def stream(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        model: str | None = None,
    ) -> AsyncIterator[str]:
        """
        Streaming completion. Yields text chunks as they arrive.
        Use with SSE endpoints.
        """
        model = model or self._settings.nvidia_model
        max_tokens = max_tokens or self._settings.llm_max_tokens
        temperature = temperature if temperature is not None else self._settings.llm_temperature

        try:
            logger.info("llm_stream_start", model=model)
            async with self._client.chat.completions.stream(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
            ) as stream_ctx:
                async for chunk in stream_ctx:
                    delta = chunk.choices[0].delta.content if chunk.choices else None
                    if delta:
                        yield delta

            logger.info("llm_stream_complete")

        except APITimeoutError as exc:
            raise LLMTimeoutError("LLM stream timed out.") from exc
        except APIConnectionError as exc:
            raise LLMError(f"LLM stream connection failed: {exc}") from exc
        except Exception as exc:
            logger.error("llm_stream_error", error=str(exc))
            raise LLMError(f"LLM stream error: {exc}") from exc


# Singleton
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
