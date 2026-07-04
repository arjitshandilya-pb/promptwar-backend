"""
Security utilities: input sanitization, prompt injection detection, JWT.
All security checks are centralized here — never scattered through the codebase.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError, PromptInjectionError

# ── Prompt injection patterns ─────────────────────────────────────────────────
_INJECTION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"ignore\s+(all\s+)?previous\s+instructions?", re.IGNORECASE),
    re.compile(r"disregard\s+(all\s+)?prior\s+(instructions?|context)", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+a", re.IGNORECASE),
    re.compile(r"act\s+as\s+(if\s+you\s+are|a)\s+", re.IGNORECASE),
    re.compile(r"(system\s*prompt|jailbreak|DAN\s+mode)", re.IGNORECASE),
    re.compile(r"<\s*(script|iframe|object|embed)", re.IGNORECASE),
    re.compile(r"\\n\\n(human|assistant|system)\s*:", re.IGNORECASE),
    re.compile(r"reveal\s+(your|the)\s+(system\s+)?prompt", re.IGNORECASE),
    re.compile(r"forget\s+(everything|all)\s+(you|above)", re.IGNORECASE),
]

# ── XSS-dangerous characters for output sanitization ─────────────────────────
_HTML_ESCAPE_TABLE: dict[str, str] = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
}


def sanitize_input(text: str) -> str:
    """
    Strip null bytes, limit length, and reject prompt injection attempts.
    Raises PromptInjectionError if injection is detected.
    """
    settings = get_settings()

    # Remove null bytes and control characters except newlines/tabs
    cleaned = re.sub(r"[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]", "", text)

    # Enforce maximum input length
    if len(cleaned) > settings.max_input_length:
        cleaned = cleaned[: settings.max_input_length]

    # Prompt injection detection
    for pattern in _INJECTION_PATTERNS:
        if pattern.search(cleaned):
            raise PromptInjectionError(
                "Input contains potentially malicious instructions.",
                {"pattern": pattern.pattern},
            )

    return cleaned.strip()


def sanitize_output(text: str) -> str:
    """Escape HTML entities to prevent XSS in rendered content."""
    return "".join(_HTML_ESCAPE_TABLE.get(c, c) for c in text)


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta
        or timedelta(minutes=settings.jwt_access_token_expire_minutes)
    )
    to_encode["exp"] = expire
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and verify a JWT token. Raises AuthenticationError on failure."""
    settings = get_settings()
    try:
        payload = jwt.decode(
            token, settings.secret_key, algorithms=[settings.jwt_algorithm]
        )
        return payload
    except JWTError as exc:
        raise AuthenticationError(f"Invalid token: {exc}") from exc
