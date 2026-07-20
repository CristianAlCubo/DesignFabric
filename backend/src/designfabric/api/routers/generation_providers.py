"""Catálogo de providers y readiness de generación IA."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from designfabric.api.schemas import (
    GenerationProvidersResponse,
    GenerationReadinessResponse,
    ProviderInfoSchema,
)
from designfabric.core.config import Settings, get_settings
from designfabric.core.generation.readiness import GenerationReadiness, probe_readiness

router = APIRouter(prefix="/api/generation", tags=["generation-providers"])

_LLM_CATALOG: tuple[tuple[str, str, bool], ...] = (
    ("ollama", "Ollama", True),
    ("openrouter", "OpenRouter", False),
    ("test", "Test (texto fijo)", False),
)

_IMAGE_CATALOG: tuple[tuple[str, str, bool], ...] = (
    ("flux", "FLUX.2 Klein", True),
    ("openrouter", "OpenRouter", False),
    ("test", "Test (imagen fija)", False),
)


def _providers_from_readiness(ready: GenerationReadiness) -> GenerationProvidersResponse:
    def llm_available(provider_id: str, requires_local_ai: bool) -> bool:
        if provider_id == "openrouter":
            return ready.providers.openrouter_llm
        if provider_id == "test":
            return ready.providers.test_llm
        if not requires_local_ai:
            return True
        return ready.providers.ollama if provider_id == "ollama" else False

    def image_available(provider_id: str, requires_local_ai: bool) -> bool:
        if provider_id == "openrouter":
            return ready.providers.openrouter_image
        if provider_id == "test":
            return ready.providers.test_image
        if not requires_local_ai:
            return True
        return ready.providers.flux if provider_id == "flux" else False

    return GenerationProvidersResponse(
        llm=[
            ProviderInfoSchema(
                id=pid,
                label=label,
                available=llm_available(pid, requires),
                requires_local_ai=requires,
            )
            for pid, label, requires in _LLM_CATALOG
        ],
        image=[
            ProviderInfoSchema(
                id=pid,
                label=label,
                available=image_available(pid, requires),
                requires_local_ai=requires,
            )
            for pid, label, requires in _IMAGE_CATALOG
        ],
    )


@router.get("/readiness", response_model=GenerationReadinessResponse)
def get_generation_readiness(
    settings: Settings = Depends(get_settings),
) -> GenerationReadinessResponse:
    """Estado completo de readiness (deps, Ollama, pesos FLUX, CUDA). Solo reporte."""
    return GenerationReadinessResponse.model_validate(probe_readiness(settings).to_dict())


@router.get("/providers", response_model=GenerationProvidersResponse)
def get_generation_providers(
    settings: Settings = Depends(get_settings),
) -> GenerationProvidersResponse:
    """Lista providers LLM e imagen; `available` deriva del probe de readiness."""
    return _providers_from_readiness(probe_readiness(settings))
