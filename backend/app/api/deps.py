"""
FastAPI dependency injection providers.
All shared dependencies are injected here — never instantiated in route handlers.
"""
from __future__ import annotations

from fastapi import Depends, Request

from app.core.rate_limiter import RateLimiter, get_rate_limiter
from app.services.discovery_service import DiscoveryService
from app.services.story_service import StoryService
from app.services.gems_service import GemsService
from app.services.etiquette_service import EtiquetteService
from app.services.festival_service import FestivalService
from app.services.tour_service import TourService
from app.services.timeline_service import TimelineService
from app.services.food_service import FoodService
from app.services.chat_service import ChatService


def get_client_ip(request: Request) -> str:
    """Extract real client IP, respecting X-Forwarded-For from proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


async def ai_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    """Dependency that applies AI-tier rate limiting."""
    ip = get_client_ip(request)
    await limiter.check(ip, tier="ai")


async def general_rate_limit(
    request: Request,
    limiter: RateLimiter = Depends(get_rate_limiter),
) -> None:
    """Dependency that applies general rate limiting."""
    ip = get_client_ip(request)
    await limiter.check(ip, tier="general")


# Service factories — single responsibility, one place to swap implementations
def get_discovery_service() -> DiscoveryService:
    return DiscoveryService()

def get_story_service() -> StoryService:
    return StoryService()

def get_gems_service() -> GemsService:
    return GemsService()

def get_etiquette_service() -> EtiquetteService:
    return EtiquetteService()

def get_festival_service() -> FestivalService:
    return FestivalService()

def get_tour_service() -> TourService:
    return TourService()

def get_timeline_service() -> TimelineService:
    return TimelineService()

def get_food_service() -> FoodService:
    return FoodService()

def get_chat_service() -> ChatService:
    return ChatService()
