"""
Application configuration via pydantic-settings.
All secrets are loaded from environment variables — never hardcoded.
"""
from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────────────────────────
    app_name: str = "WanderMind"
    app_version: str = "1.0.0"
    environment: Literal["development", "staging", "production"] = "development"
    debug: bool = False
    secret_key: str = Field(..., min_length=32)

    # ── NVIDIA NIM / LLM ─────────────────────────────────────────────────────
    nvidia_api_key: str = Field(..., min_length=10)
    nvidia_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_model: str = "deepseek-ai/deepseek-v4-0709"
    llm_timeout_seconds: int = 120
    llm_max_retries: int = 3
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.7

    # ── Rate Limiting ─────────────────────────────────────────────────────────
    rate_limit_ai_rpm: int = 10        # AI endpoints: requests per minute
    rate_limit_general_rpm: int = 60   # General endpoints
    rate_limit_burst: int = 5

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: list[str] = [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]

    # ── Database ──────────────────────────────────────────────────────────────
    database_url: str = "sqlite:///./wandermind.db"

    # ── Vector Store (pure-Python TF-IDF, no external deps) ───────────────────
    gems_data_path: str = "./data/hidden_gems.json"

    # ── Cache ─────────────────────────────────────────────────────────────────
    cache_ttl_seconds: int = 3600
    cache_max_size: int = 512

    # ── Security ──────────────────────────────────────────────────────────────
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60
    max_input_length: int = 2000

    @field_validator("llm_temperature")
    @classmethod
    def validate_temperature(cls, v: float) -> float:
        if not 0.0 <= v <= 2.0:
            raise ValueError("Temperature must be between 0.0 and 2.0")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached settings singleton — parsed once at startup."""
    return Settings()  # type: ignore[call-arg]
