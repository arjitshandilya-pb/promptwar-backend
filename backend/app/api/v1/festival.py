"""
FestivalOracle router.
POST /api/v1/festivals
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ai_rate_limit, get_festival_service
from app.models.schemas import FestivalRequest, FestivalResponse
from app.services.festival_service import FestivalService

router = APIRouter(prefix="/festivals", tags=["Festivals"])


@router.post(
    "",
    response_model=FestivalResponse,
    summary="Predict upcoming festivals",
    description="AI-powered festival and cultural event prediction for a destination.",
    dependencies=[Depends(ai_rate_limit)],
)
async def get_festivals(
    req: FestivalRequest,
    service: FestivalService = Depends(get_festival_service),
) -> FestivalResponse:
    return await service.get_festivals(req)
