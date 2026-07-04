"""
Gems Service — HiddenGem Radar using RAG over ChromaDB vector store.
Combines semantic search with AI-generated pitch text for each gem.
"""
from __future__ import annotations

import asyncio

from app.core.security import sanitize_input
from app.infrastructure.cache import get_cache, make_cache_key
from app.infrastructure.llm_client import get_llm_client
from app.infrastructure.vector_store import get_vector_store
from app.models.schemas import GemsRequest, GemsResponse, GemItem


_GEM_PITCH_SYSTEM = """
You are a travel copywriter. Given a hidden gem location, write a single compelling 
2-sentence pitch that makes a traveler desperately want to go there.
Focus on what makes it unique, authentic, and undiscovered.
Respond with ONLY the pitch text — no labels, no JSON, just the sentences.
""".strip()


class GemsService:
    async def find_gems(self, req: GemsRequest) -> GemsResponse:
        clean_query = sanitize_input(req.query)

        cache = get_cache()
        cache_key = make_cache_key("gems", clean_query, str(req.n_results), req.continent or "all")
        cached = await cache.get(cache_key)
        if cached:
            return GemsResponse(**cached)

        vs = get_vector_store()
        where = {"continent": req.continent} if req.continent else None
        hits = vs.search(clean_query, n_results=req.n_results, where=where)

        # Generate AI pitch for each gem in parallel
        llm = get_llm_client()
        pitches = await asyncio.gather(
            *[
                llm.complete(
                    messages=[
                        {"role": "system", "content": _GEM_PITCH_SYSTEM},
                        {
                            "role": "user",
                            "content": f"Location: {hit['metadata']['name']}, {hit['metadata']['country']}\n"
                                       f"Description: {hit['document']}",
                        },
                    ],
                    max_tokens=120,
                    temperature=0.85,
                )
                for hit in hits
            ],
            return_exceptions=True,
        )

        gems = []
        for hit, pitch in zip(hits, pitches):
            meta = hit["metadata"]
            ai_pitch = pitch if isinstance(pitch, str) else "A truly remarkable hidden gem awaiting discovery."
            gems.append(
                GemItem(
                    name=meta["name"],
                    country=meta["country"],
                    description=hit["document"],
                    authenticity_score=float(meta.get("authenticity_score", 7.0)),
                    tourist_density=meta.get("tourist_density", "low"),
                    best_season=meta.get("best_season", "year-round"),
                    tags=meta.get("tags", []),
                    lat=float(meta.get("lat", 0.0)),
                    lng=float(meta.get("lng", 0.0)),
                    similarity=hit["similarity"],
                    ai_pitch=ai_pitch.strip(),
                )
            )

        result = GemsResponse(gems=gems, total=len(gems))
        await cache.set(cache_key, result.model_dump(), ttl=1800)
        return result
