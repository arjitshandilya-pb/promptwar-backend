"""
Story Service — CulturalLens immersive narrative generator.
Returns an async generator for SSE streaming.
"""
from __future__ import annotations

from typing import AsyncIterator

from app.core.security import sanitize_input
from app.infrastructure.llm_client import get_llm_client
from app.prompts.system_prompts import STORY_SYSTEM


class StoryService:
    async def generate_story_stream(
        self,
        destination: str,
        pov: str = "first-person traveler",
    ) -> AsyncIterator[str]:
        clean_dest = sanitize_input(destination)
        clean_pov = sanitize_input(pov)

        user_content = (
            f"Write an immersive CulturalLens story for: {clean_dest}\n"
            f"Narrative POV: {clean_pov}"
        )

        llm = get_llm_client()
        async for chunk in llm.stream(
            messages=[
                {"role": "system", "content": STORY_SYSTEM},
                {"role": "user", "content": user_content},
            ],
            temperature=0.9,
            max_tokens=600,
        ):
            yield chunk
