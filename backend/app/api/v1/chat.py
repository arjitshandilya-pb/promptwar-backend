"""
LocalVoice streaming chat router.
POST /api/v1/chat/stream
"""
from __future__ import annotations

import json
from typing import AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from app.api.deps import ai_rate_limit, get_chat_service
from app.models.schemas import ChatRequest
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["LocalVoice Chat"])


async def _sse_wrap(gen: AsyncIterator[str]) -> AsyncIterator[str]:
    try:
        async for token in gen:
            yield f"data: {json.dumps({'token': token})}\n\n"
        yield "data: [DONE]\n\n"
    except Exception as exc:
        yield f"data: {json.dumps({'error': str(exc)})}\n\n"


@router.post(
    "/stream",
    summary="Stream LocalVoice guide response",
    description="RAG-augmented streaming AI local guide conversation.",
    dependencies=[Depends(ai_rate_limit)],
)
async def stream_chat(
    req: ChatRequest,
    service: ChatService = Depends(get_chat_service),
) -> StreamingResponse:
    gen = service.stream_response(req)
    return StreamingResponse(
        _sse_wrap(gen),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
