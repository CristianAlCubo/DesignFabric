"""Catálogo de providers primitivos de generación (LLM e imagen)."""

from __future__ import annotations

from fastapi import APIRouter

from designfabric.api.local_ai import LOCAL_AI_AVAILABLE
from designfabric.api.schemas import GenerationProvidersResponse, ProviderInfoSchema

router = APIRouter(prefix="/api/generation", tags=["generation-providers"])

_LLM_CATALOG: tuple[tuple[str, str, bool], ...] = (
    ("ollama", "Ollama", True),
    ("test", "Test (texto fijo)", False),
)

_IMAGE_CATALOG: tuple[tuple[str, str, bool], ...] = (
    ("flux", "FLUX.2 Klein", True),
    ("test", "Test (imagen fija)", False),
)


def _to_info(provider_id: str, label: str, requires_local_ai: bool) -> ProviderInfoSchema:
    available = LOCAL_AI_AVAILABLE if requires_local_ai else True
    return ProviderInfoSchema(
        id=provider_id,
        label=label,
        available=available,
        requires_local_ai=requires_local_ai,
    )


@router.get("/providers", response_model=GenerationProvidersResponse)
def get_generation_providers() -> GenerationProvidersResponse:
    """Lista providers LLM e imagen con su disponibilidad en este entorno."""
    return GenerationProvidersResponse(
        llm=[_to_info(pid, label, requires) for pid, label, requires in _LLM_CATALOG],
        image=[_to_info(pid, label, requires) for pid, label, requires in _IMAGE_CATALOG],
    )
