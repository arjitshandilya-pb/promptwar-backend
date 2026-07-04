"""
FoodDNA culinary explorer router.
POST /api/v1/food
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ai_rate_limit, get_food_service
from app.models.schemas import FoodRequest, FoodResponse
from app.services.food_service import FoodService

router = APIRouter(prefix="/food", tags=["Food DNA"])


@router.post(
    "",
    response_model=FoodResponse,
    summary="Generate food journey",
    description="AI-curated culinary journey: street food, traditional dishes, modern fusion.",
    dependencies=[Depends(ai_rate_limit)],
)
async def get_food_journey(
    req: FoodRequest,
    service: FoodService = Depends(get_food_service),
) -> FoodResponse:
    return await service.get_food_journey(req)
