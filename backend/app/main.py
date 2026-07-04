"""
WanderMind FastAPI application factory.
Clean startup/shutdown lifecycle, global exception handlers, security middleware.
"""
from __future__ import annotations

import asyncio
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as v1_router
from app.core.config import get_settings
from app.core.exceptions import WanderMindError
from app.core.logging import configure_logging, get_logger, set_request_id
from app.infrastructure.cache import get_cache
from app.infrastructure.vector_store import get_vector_store
from app.models.schemas import HealthResponse

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan: warm up services on startup, clean up on shutdown."""
    settings = get_settings()
    configure_logging(debug=settings.debug)

    logger.info(
        "app_startup",
        app=settings.app_name,
        version=settings.app_version,
        env=settings.environment,
        model=settings.nvidia_model,
    )

    # Warm up vector store and seed hidden gems data
    vs = get_vector_store()
    data_path = Path(__file__).parent.parent / "data" / "hidden_gems.json"
    added = vs.seed_from_file(data_path)
    logger.info("vector_store_seeded", new_documents=added)

    # Start background cache cleanup task
    async def _cache_cleanup() -> None:
        cache = get_cache()
        while True:
            await asyncio.sleep(300)
            removed = await cache.purge_expired()
            if removed:
                logger.info("cache_cleanup", removed=removed)

    cleanup_task = asyncio.create_task(_cache_cleanup())

    yield

    # Shutdown
    cleanup_task.cancel()
    logger.info("app_shutdown")


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(
        title="WanderMind API",
        description=(
            "AI-powered destination discovery and cultural experience platform. "
            "Powered by NVIDIA NIM / DeepSeek V4."
        ),
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ── CORS ──────────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ── Request ID middleware ──────────────────────────────────────────────────
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore
        rid = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        set_request_id(rid)
        response = await call_next(request)
        response.headers["X-Request-ID"] = rid
        return response

    # ── Security headers middleware ────────────────────────────────────────────
    @app.middleware("http")
    async def security_headers(request: Request, call_next):  # type: ignore
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # ── Exception handlers ────────────────────────────────────────────────────
    @app.exception_handler(WanderMindError)
    async def wandermind_exception_handler(
        request: Request, exc: WanderMindError
    ) -> JSONResponse:
        logger.warning(
            "domain_error",
            error_code=exc.error_code,
            message=exc.message,
            path=str(request.url.path),
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error_code": exc.error_code,
                "message": exc.message,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error("unhandled_error", error=str(exc), path=str(request.url.path))
        return JSONResponse(
            status_code=500,
            content={
                "error_code": "INTERNAL_ERROR",
                "message": "An unexpected error occurred.",
                "details": {},
            },
        )

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(v1_router)

    @app.get("/api/v1/health", response_model=HealthResponse, tags=["Health"])
    async def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            version=settings.app_version,
            environment=settings.environment,
        )

    return app


app = create_app()
