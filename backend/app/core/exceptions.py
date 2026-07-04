"""
Custom exception hierarchy for clean error handling.
Maps domain exceptions to HTTP status codes without leaking internals.
"""
from __future__ import annotations

from typing import Any


class WanderMindError(Exception):
    """Base exception for all application errors."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(WanderMindError):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class RateLimitError(WanderMindError):
    status_code = 429
    error_code = "RATE_LIMIT_EXCEEDED"


class LLMError(WanderMindError):
    status_code = 503
    error_code = "LLM_UNAVAILABLE"


class LLMTimeoutError(LLMError):
    status_code = 504
    error_code = "LLM_TIMEOUT"


class PromptInjectionError(WanderMindError):
    status_code = 400
    error_code = "PROMPT_INJECTION_DETECTED"


class NotFoundError(WanderMindError):
    status_code = 404
    error_code = "NOT_FOUND"


class AuthenticationError(WanderMindError):
    status_code = 401
    error_code = "AUTHENTICATION_REQUIRED"


class AuthorizationError(WanderMindError):
    status_code = 403
    error_code = "FORBIDDEN"
