"""Reporta qué features/módulos del backend están disponibles en este entorno."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from designfabricv2.api.registry import FEATURE_REGISTRY, LOCAL_AI_AVAILABLE

router = APIRouter(tags=["features"])


class FeaturesResponse(BaseModel):
    local_ai_available: bool
    modules: list[str]


@router.get("/features", response_model=FeaturesResponse)
def get_features() -> FeaturesResponse:
    return FeaturesResponse(
        local_ai_available=LOCAL_AI_AVAILABLE,
        modules=[module.name for module in FEATURE_REGISTRY],
    )
