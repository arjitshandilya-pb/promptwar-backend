"""
Food Service — FoodDNA culinary explorer.
"""
from __future__ import annotations

from app.core.security import sanitize_input
from app.infrastructure.cache import get_cache, make_cache_key
from app.infrastructure.llm_client import get_llm_client
from app.models.schemas import FoodRequest, FoodResponse, FoodStop
from app.prompts.system_prompts import FOOD_SYSTEM


class FoodService:
    async def get_food_journey(self, req: FoodRequest) -> FoodResponse:
        clean_dest = sanitize_input(req.destination)
        restrictions = ", ".join(req.dietary_restrictions) if req.dietary_restrictions else "none"

        cache = get_cache()
        cache_key = make_cache_key("food", clean_dest, restrictions)
        cached = await cache.get(cache_key)
        if cached:
            return FoodResponse(**cached)

        user_content = (
            f"Create a food journey for: {clean_dest}\n"
            f"Dietary restrictions: {restrictions}"
        )

        llm = get_llm_client()
        raw = await llm.complete_json(
            messages=[
                {"role": "system", "content": FOOD_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.75,
            max_tokens=2000,
        )

        food_stops = [FoodStop(**s) for s in raw.get("food_journey", [])]
        result = FoodResponse(
            destination=clean_dest,
            food_journey=food_stops,
            food_culture_note=raw.get("food_culture_note", ""),
            beverage_pairing=raw.get("beverage_pairing", ""),
        )
        await cache.set(cache_key, result.model_dump(), ttl=7200)
        return result
