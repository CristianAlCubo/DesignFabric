"""Tests del catálogo GET /api/generation/providers."""

from __future__ import annotations

from designfabric.api.registry import LOCAL_AI_AVAILABLE


def test_generation_providers_catalog(client):
    response = client.get("/api/generation/providers")
    assert response.status_code == 200
    body = response.json()

    llm_ids = {p["id"]: p for p in body["llm"]}
    image_ids = {p["id"]: p for p in body["image"]}

    assert llm_ids["test"]["available"] is True
    assert llm_ids["test"]["requires_local_ai"] is False
    assert image_ids["test"]["available"] is True
    assert image_ids["test"]["requires_local_ai"] is False

    assert llm_ids["ollama"]["requires_local_ai"] is True
    assert image_ids["flux"]["requires_local_ai"] is True
    assert llm_ids["ollama"]["available"] is LOCAL_AI_AVAILABLE
    assert image_ids["flux"]["available"] is LOCAL_AI_AVAILABLE
