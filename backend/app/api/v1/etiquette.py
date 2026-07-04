"""
EtiquetteAI router.
POST /api/v1/etiquette
"""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import ai_rate_limit, get_etiquette_service
from app.models.schemas import EtiquetteRequest, EtiquetteResponse
from app.services.etiquette_service import EtiquetteService

router = APIRouter(prefix="/etiquette", tags=["Etiquette"])


@router.post(
    "",
    response_model=EtiquetteResponse,
    summary="Get cultural etiquette guide",
    description="AI-powered cultural intelligence: do's, don'ts, local phrases, and customs.",
    dependencies=[Depends(ai_rate_limit)],
)
async def get_etiquette(
    req: EtiquetteRequest,
    service: EtiquetteService = Depends(get_etiquette_service),
) -> EtiquetteResponse:
    return await service.get_etiquette(req)
