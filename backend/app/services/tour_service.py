"""
Tour Service — WalkingTour Architect AI walking tour generator.
"""
from __future__ import annotations

from app.core.security import sanitize_input
from app.infrastructure.cache import get_cache, make_cache_key
from app.infrastructure.llm_client import get_llm_client
from app.models.schemas import TourRequest, TourResponse, TourStop
from app.prompts.system_prompts import TOUR_SYSTEM


class TourService:
    async def generate_tour(self, req: TourRequest) -> TourResponse:
        clean_dest = sanitize_input(req.destination)
        clean_theme = sanitize_input(req.theme)

        cache = get_cache()
        cache_key = make_cache_key("tour", clean_dest, clean_theme, str(req.duration_hours))
        cached = await cache.get(cache_key)
        if cached:
            return TourResponse(**cached)

        user_content = (
            f"Create a walking tour of {clean_dest}\n"
            f"Theme: {clean_theme}\n"
            f"Target duration: {req.duration_hours} hours"
        )

        llm = get_llm_client()
        raw = await llm.complete_json(
            messages=[
                {"role": "system", "content": TOUR_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.7,
            max_tokens=2000,
        )

        stops = [TourStop(**s) for s in raw.get("stops", [])]
        result = TourResponse(
            destination=clean_dest,
            theme=clean_theme,
            total_duration=raw.get("total_duration", f"{req.duration_hours} hours"),
            total_distance_km=float(raw.get("total_distance_km", 2.0)),
            stops=stops,
            start_tip=raw.get("start_tip", ""),
        )
        await cache.set(cache_key, result.model_dump(), ttl=7200)
        return result
