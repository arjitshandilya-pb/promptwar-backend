"""
v1 API router — mounts all sub-routers under /api/v1
"""
from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import discover, story, gems, etiquette, festival, tour, timeline, food, chat

router = APIRouter(prefix="/api/v1")

router.include_router(discover.router)
router.include_router(story.router)
router.include_router(gems.router)
router.include_router(etiquette.router)
router.include_router(festival.router)
router.include_router(tour.router)
router.include_router(timeline.router)
router.include_router(food.router)
router.include_router(chat.router)
