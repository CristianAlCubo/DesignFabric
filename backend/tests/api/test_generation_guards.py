"""Tests de guards de readiness al encolar jobs."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from designfabric.api.generation_guards import require_generation_ready
from designfabric.core.generation.readiness import (
    CudaStatus,
    FluxStatus,
    GenerationReadiness,
    LocalAiStatus,
    OllamaStatus,
    ProviderReadiness,
)


def _ready(**overrides) -> GenerationReadiness:
    base = dict(
        local_ai=LocalAiStatus(available=True, missing=()),
        ollama=OllamaStatus(host="http://h", reachable=True, models=("gemma3:4b",)),
        flux=FluxStatus(model_id="m", weights_present=True, cache_hint="/c"),
        cuda=CudaStatus(available=True, device_name="g"),
        providers=ProviderReadiness(ollama=True, flux=True),
    )
    base.update(overrides)
    return GenerationReadiness(**base)


def test_require_allows_test_providers() -> None:
    require_generation_ready(
        llm_provider="test",
        image_provider="test",
        readiness=_ready(providers=ProviderReadiness(ollama=False, flux=False)),
    )


def test_require_rejects_ollama_when_unreachable() -> None:
    with pytest.raises(HTTPException) as exc:
        require_generation_ready(
            llm_provider="ollama",
            readiness=_ready(
                ollama=OllamaStatus(host="http://h", reachable=False, error="refused"),
                providers=ProviderReadiness(ollama=False, flux=True),
            ),
        )
    assert exc.value.status_code == 503


def test_require_rejects_missing_ollama_model() -> None:
    with pytest.raises(HTTPException) as exc:
        require_generation_ready(
            llm_provider="ollama",
            ollama_model="nope:1b",
            readiness=_ready(),
        )
    assert "nope:1b" in exc.value.detail


def test_require_rejects_flux_without_weights() -> None:
    with pytest.raises(HTTPException) as exc:
        require_generation_ready(
            image_provider="flux",
            readiness=_ready(
                flux=FluxStatus(model_id="m", weights_present=False),
                providers=ProviderReadiness(ollama=True, flux=False),
            ),
        )
    assert "Pesos" in exc.value.detail or "caché" in exc.value.detail
