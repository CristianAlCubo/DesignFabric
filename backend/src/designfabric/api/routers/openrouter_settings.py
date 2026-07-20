"""Endpoints de configuración OpenRouter y catálogo de modelos."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, HTTPException, Query

from designfabric.api.schemas import (
    OpenRouterModelSchema,
    OpenRouterModelsResponse,
    OpenRouterSettingsPublicResponse,
    OpenRouterSettingsUpdateRequest,
)
from designfabric.core.generation.openrouter.client import OpenRouterClient
from designfabric.core.generation.openrouter.errors import (
    OpenRouterAuthError,
    OpenRouterConfigError,
    OpenRouterError,
)
from designfabric.core.generation.openrouter.models_cache import get_models_cache
from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime

router = APIRouter(tags=["openrouter"])


@router.get("/api/settings/openrouter", response_model=OpenRouterSettingsPublicResponse)
def get_openrouter_settings() -> OpenRouterSettingsPublicResponse:
    runtime = get_openrouter_runtime()
    runtime.seed_from_settings()
    snap = runtime.snapshot()
    return OpenRouterSettingsPublicResponse(
        configured=snap.configured,
        text_model_id=snap.text_model_id,
        image_model_id=snap.image_model_id,
    )


@router.put("/api/settings/openrouter", response_model=OpenRouterSettingsPublicResponse)
def put_openrouter_settings(payload: OpenRouterSettingsUpdateRequest) -> OpenRouterSettingsPublicResponse:
    runtime = get_openrouter_runtime()
    runtime.seed_from_settings()
    snap = runtime.update(
        api_key=payload.api_key,
        clear_api_key=payload.clear_api_key,
        text_model_id=payload.text_model_id,
        image_model_id=payload.image_model_id,
        clear_text_model=payload.clear_text_model,
        clear_image_model=payload.clear_image_model,
    )
    if payload.clear_api_key or payload.api_key is not None:
        get_models_cache().invalidate()
    return OpenRouterSettingsPublicResponse(
        configured=snap.configured,
        text_model_id=snap.text_model_id,
        image_model_id=snap.image_model_id,
    )


@router.get("/api/openrouter/models", response_model=OpenRouterModelsResponse)
def list_openrouter_models(
    modality: Literal["text", "image"] = Query(..., description="Modalidad de salida"),
    q: str | None = Query(None, description="Filtro rápido por id/nombre"),
) -> OpenRouterModelsResponse:
    runtime = get_openrouter_runtime()
    runtime.seed_from_settings()
    snap = runtime.snapshot()
    if not snap.configured:
        raise HTTPException(status_code=503, detail="OpenRouter no está configurado (falta API key).")

    cache = get_models_cache()

    def fetch() -> list:
        client = OpenRouterClient(snap.api_key or "", base_url=snap.base_url)
        return client.list_models(modality)

    try:
        models = cache.get_or_fetch(modality, fetch)
    except OpenRouterAuthError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc
    except OpenRouterConfigError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except OpenRouterError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    filtered = OpenRouterClient.filter_models(models, q)
    return OpenRouterModelsResponse(
        models=[
            OpenRouterModelSchema(
                id=m.id,
                name=m.name,
                output_modalities=list(m.output_modalities),
            )
            for m in filtered
        ]
    )
