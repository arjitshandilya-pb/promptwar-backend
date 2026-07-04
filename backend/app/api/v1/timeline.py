"""
TimeMachine historical timeline router.
POST /api/v1/timeline
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ai_rate_limit, get_timeline_service
from app.models.schemas import TimelineRequest, TimelineResponse
from app.services.timeline_service import TimelineService

router = APIRouter(prefix="/timeline", tags=["Timeline"])


@router.post(
    "",
    response_model=TimelineResponse,
    summary="Generate historical timeline",
    description="AI-generated chronological history of a destination, era by era.",
    dependencies=[Depends(ai_rate_limit)],
)
async def get_timeline(
    req: TimelineRequest,
    service: TimelineService = Depends(get_timeline_service),
) -> TimelineResponse:
    return await service.get_timeline(req)
