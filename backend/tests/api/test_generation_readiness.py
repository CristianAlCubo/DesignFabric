"""Tests de GET /api/generation/readiness y /providers."""

from __future__ import annotations

import pytest

from designfabric.core.generation.readiness import (
    CudaStatus,
    FluxStatus,
    GenerationReadiness,
    LocalAiStatus,
    OllamaStatus,
    ProviderReadiness,
)


@pytest.fixture
def fake_ready() -> GenerationReadiness:
    return GenerationReadiness(
        local_ai=LocalAiStatus(available=True, missing=()),
        ollama=OllamaStatus(
            host="http://localhost:11434",
            reachable=True,
            models=("gemma3:4b",),
        ),
        flux=FluxStatus(
            model_id="black-forest-labs/FLUX.2-klein-4B",
            weights_present=True,
            cache_hint="/tmp/hf",
        ),
        cuda=CudaStatus(available=True, device_name="Fake GPU"),
        providers=ProviderReadiness(ollama=True, flux=True),
    )


def test_readiness_endpoint_shape(client, monkeypatch, fake_ready):
    monkeypatch.setattr(
        "designfabric.api.routers.generation_providers.probe_readiness",
        lambda settings=None: fake_ready,
    )
    response = client.get("/api/generation/readiness")
    assert response.status_code == 200
    body = response.json()
    assert body["local_ai"]["available"] is True
    assert body["ollama"]["reachable"] is True
    assert body["ollama"]["models"] == ["gemma3:4b"]
    assert body["flux"]["weights_present"] is True
    assert body["cuda"]["available"] is True
    assert body["providers"]["ollama"] is True
    assert body["providers"]["flux"] is True
    assert body["providers"]["test_llm"] is True


def test_providers_derive_from_readiness(client, monkeypatch, fake_ready):
    monkeypatch.setattr(
        "designfabric.api.routers.generation_providers.probe_readiness",
        lambda settings=None: fake_ready,
    )
    response = client.get("/api/generation/providers")
    assert response.status_code == 200
    body = response.json()
    by_id = {item["id"]: item for item in body["llm"] + body["image"]}
    assert by_id["ollama"]["available"] is True
    assert by_id["flux"]["available"] is True
    assert by_id["test"]["available"] is True


def test_providers_mark_unavailable_when_probe_says_so(client, monkeypatch):
    ready = GenerationReadiness(
        local_ai=LocalAiStatus(available=True, missing=()),
        ollama=OllamaStatus(host="http://localhost:11434", reachable=False, error="down"),
        flux=FluxStatus(model_id="m", weights_present=False, cache_hint=None),
        cuda=CudaStatus(available=False),
        providers=ProviderReadiness(ollama=False, flux=False),
    )
    monkeypatch.setattr(
        "designfabric.api.routers.generation_providers.probe_readiness",
        lambda settings=None: ready,
    )
    body = client.get("/api/generation/providers").json()
    by_id = {item["id"]: item for item in body["llm"] + body["image"]}
    assert by_id["ollama"]["available"] is False
    assert by_id["flux"]["available"] is False
    assert by_id["test"]["available"] is True
