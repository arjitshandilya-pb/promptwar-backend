"""
Destination discovery router.
POST /api/v1/discover
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ai_rate_limit, get_discovery_service
from app.models.schemas import DiscoverRequest, DiscoverResponse
from app.services.discovery_service import DiscoveryService

router = APIRouter(prefix="/discover", tags=["Discover"])


@router.post(
    "",
    response_model=DiscoverResponse,
    summary="Discover destinations",
    description="AI-powered destination recommendations based on natural language travel desires.",
    dependencies=[Depends(ai_rate_limit)],
)
async def discover_destinations(
    req: DiscoverRequest,
    service: DiscoveryService = Depends(get_discovery_service),
) -> DiscoverResponse:
    return await service.discover(req)
