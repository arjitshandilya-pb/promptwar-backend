"""
Hidden Gems router — HiddenGem Radar RAG endpoint.
POST /api/v1/gems
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ai_rate_limit, get_gems_service
from app.models.schemas import GemsRequest, GemsResponse
from app.services.gems_service import GemsService

router = APIRouter(prefix="/gems", tags=["Hidden Gems"])


@router.post(
    "",
    response_model=GemsResponse,
    summary="Find hidden gems",
    description="Semantic search over curated off-the-beaten-path destinations with AI-generated pitches.",
    dependencies=[Depends(ai_rate_limit)],
)
async def find_hidden_gems(
    req: GemsRequest,
    service: GemsService = Depends(get_gems_service),
) -> GemsResponse:
    return await service.find_gems(req)
