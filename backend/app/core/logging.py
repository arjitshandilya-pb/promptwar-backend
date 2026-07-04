"""
Structured JSON logging with request tracing.
All log fields are typed and never contain secrets.
"""
from __future__ import annotations

import logging
import sys
import uuid
from contextvars import ContextVar
from typing import Any

import structlog

# ── Request-scoped correlation ID ─────────────────────────────────────────────
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    return request_id_var.get() or str(uuid.uuid4())


def set_request_id(rid: str) -> None:
    request_id_var.set(rid)


# ── Structlog processors chain ────────────────────────────────────────────────
def add_request_id(
    logger: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    event_dict["request_id"] = get_request_id()
    return event_dict


def drop_color_message_key(
    logger: Any, method: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """Remove uvicorn's color_message to keep logs clean."""
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(debug: bool = False) -> None:
    """Configure structlog for JSON structured logging."""
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        add_request_id,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        drop_color_message_key,
    ]

    if debug:
        renderer = structlog.dev.ConsoleRenderer()
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.DEBUG if debug else logging.INFO)

    # Silence noisy libraries
    for noisy in ("httpx", "httpcore", "uvicorn.access"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a named bound logger."""
    return structlog.get_logger(name)
