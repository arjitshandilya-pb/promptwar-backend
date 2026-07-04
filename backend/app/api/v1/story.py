"""
CulturalLens story streaming router.
GET /api/v1/story/stream?destination=...
Uses Server-Sent Events for real-time token streaming.
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.api.deps import ai_rate_limit, get_story_service
from app.core.security import sanitize_input
from app.services.story_service import StoryService

router = APIRouter(prefix="/story", tags=["CulturalLens Story"])


async def _sse_stream(gen: AsyncIterator[str]) -> AsyncIterator[str]:
    """Wrap token stream in SSE protocol format."""
    try:
        async for token in gen:
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"


@router.get(
    "/stream",
    summary="Stream immersive destination story",
    description="Returns a cinematic cultural story as a Server-Sent Event stream.",
    dependencies=[Depends(ai_rate_limit)],
)
async def stream_story(
    destination: str = Query(..., min_length=2, max_length=200),
    pov: str = Query(default="first-person traveler", max_length=100),
    service: StoryService = Depends(get_story_service),
) -> StreamingResponse:
    clean_dest = sanitize_input(destination)
    clean_pov = sanitize_input(pov)
    gen = service.generate_story_stream(clean_dest, clean_pov)
    return StreamingResponse(
        _sse_stream(gen),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
