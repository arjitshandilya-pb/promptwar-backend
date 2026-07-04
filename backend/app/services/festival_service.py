"""
Festival Service — FestivalOracle event prediction engine.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.core.security import sanitize_input
from app.infrastructure.cache import get_cache, make_cache_key
from app.infrastructure.llm_client import get_llm_client
from app.models.schemas import FestivalRequest, FestivalResponse, Festival
from app.prompts.system_prompts import FESTIVAL_SYSTEM


class FestivalService:
    async def get_festivals(self, req: FestivalRequest) -> FestivalResponse:
        clean_dest = sanitize_input(req.destination)
        now = datetime.now(timezone.utc)
        current_month = now.strftime("%B %Y")

        cache = get_cache()
        cache_key = make_cache_key("festival", clean_dest, current_month, str(req.months_ahead))
        cached = await cache.get(cache_key)
        if cached:
            return FestivalResponse(**cached)

        user_content = (
            f"Destination: {clean_dest}\n"
            f"Current date: {current_month}\n"
            f"Show festivals/events for the next {req.months_ahead} months."
        )

        llm = get_llm_client()
        raw = await llm.complete_json(
            messages=[
                {"role": "system", "content": FESTIVAL_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.5,
            max_tokens=1500,
        )

        festivals = [Festival(**f) for f in raw.get("festivals", [])]
        result = FestivalResponse(
            destination=clean_dest,
            festivals=festivals,
            seasonal_summary=raw.get("seasonal_summary", ""),
        )
        await cache.set(cache_key, result.model_dump(), ttl=43200)  # 12h cache
        return result
