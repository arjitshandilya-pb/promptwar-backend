"""
Discovery Service — interprets traveler intent and surfaces destination recommendations.
Uses LLM with JSON mode for structured, validated output.
Results are cached by query fingerprint.
"""
from __future__ import annotations

from app.core.security import sanitize_input
from app.infrastructure.cache import get_cache, make_cache_key
from app.infrastructure.llm_client import get_llm_client
from app.models.schemas import DiscoverRequest, DiscoverResponse, Destination
from app.prompts.system_prompts import DISCOVER_SYSTEM


class DiscoveryService:
    async def discover(self, req: DiscoverRequest) -> DiscoverResponse:
        clean_query = sanitize_input(req.query)
        prefs_str = ", ".join(req.preferences) if req.preferences else "none specified"
        exclude_str = ", ".join(req.exclude_countries) if req.exclude_countries else "none"

        cache = get_cache()
        cache_key = make_cache_key("discover", clean_query, prefs_str, exclude_str)
        cached = await cache.get(cache_key)
        if cached:
            return DiscoverResponse(**cached)

        user_content = (
            f"Find me destinations for: {clean_query}\n"
            f"My travel preferences: {prefs_str}\n"
            f"Exclude these countries: {exclude_str}"
        )

        llm = get_llm_client()
        raw = await llm.complete_json(
            messages=[
                {"role": "system", "content": DISCOVER_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.8,
            max_tokens=2000,
        )

        destinations = [
            Destination(**d) for d in raw.get("destinations", [])
        ]
        result = DiscoverResponse(
            destinations=destinations,
            query_echo=clean_query,
            search_intent=raw.get("search_intent", ""),
        )
        await cache.set(cache_key, result.model_dump(), ttl=3600)
        return result
