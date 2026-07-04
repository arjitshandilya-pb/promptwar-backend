"""
Timeline Service — TimeMachine historical era generator.
"""
from __future__ import annotations

from app.core.security import sanitize_input
from app.infrastructure.cache import get_cache, make_cache_key
from app.infrastructure.llm_client import get_llm_client
from app.models.schemas import TimelineRequest, TimelineResponse, TimelineEra
from app.prompts.system_prompts import TIMELINE_SYSTEM


class TimelineService:
    async def get_timeline(self, req: TimelineRequest) -> TimelineResponse:
        clean_dest = sanitize_input(req.destination)

        cache = get_cache()
        cache_key = make_cache_key("timeline", clean_dest)
        cached = await cache.get(cache_key)
        if cached:
            return TimelineResponse(**cached)

        llm = get_llm_client()
        raw = await llm.complete_json(
            messages=[
                {"role": "system", "content": TIMELINE_SYSTEM},
                {
                    "role": "user",
                    "content": f"Generate a historical timeline for: {clean_dest}",
                },
            ],
            temperature=0.4,  # Low temp for historical accuracy
            max_tokens=2500,
        )

        eras = [TimelineEra(**e) for e in raw.get("eras", [])]
        result = TimelineResponse(
            destination=clean_dest,
            eras=eras,
            closing_reflection=raw.get("closing_reflection", ""),
        )
        await cache.set(cache_key, result.model_dump(), ttl=86400)  # History doesn't change
        return result
