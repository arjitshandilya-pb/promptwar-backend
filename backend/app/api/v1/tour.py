"""
WalkingTour Architect router.
POST /api/v1/tour
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ai_rate_limit, get_tour_service
from app.models.schemas import TourRequest, TourResponse
from app.services.tour_service import TourService

router = APIRouter(prefix="/tour", tags=["Walking Tour"])


@router.post(
    "",
    response_model=TourResponse,
    summary="Generate AI walking tour",
    description="AI-crafted 5-stop walking tour with narratives, GPS coordinates, and insider tips.",
    dependencies=[Depends(ai_rate_limit)],
)
async def generate_tour(
    req: TourRequest,
    service: TourService = Depends(get_tour_service),
) -> TourResponse:
    return await service.generate_tour(req)
