"""
Etiquette Service — EtiquetteAI cultural intelligence coach.
"""
from __future__ import annotations

from app.core.security import sanitize_input
from app.infrastructure.cache import get_cache, make_cache_key
from app.infrastructure.llm_client import get_llm_client
from app.models.schemas import EtiquetteRequest, EtiquetteResponse
from app.prompts.system_prompts import ETIQUETTE_SYSTEM


class EtiquetteService:
    async def get_etiquette(self, req: EtiquetteRequest) -> EtiquetteResponse:
        clean_dest = sanitize_input(req.destination)

        cache = get_cache()
        cache_key = make_cache_key("etiquette", clean_dest)
        cached = await cache.get(cache_key)
        if cached:
            return EtiquetteResponse(**cached)

        llm = get_llm_client()
        raw = await llm.complete_json(
            messages=[
                {"role": "system", "content": ETIQUETTE_SYSTEM},
                {
                    "role": "user",
                    "content": f"Provide complete cultural etiquette guide for: {clean_dest}",
                },
            ],
            temperature=0.3,  # Low temp for factual accuracy
            max_tokens=1500,
        )

        result = EtiquetteResponse(destination=clean_dest, **raw)
        await cache.set(cache_key, result.model_dump(), ttl=86400)  # 24h cache
        return result
