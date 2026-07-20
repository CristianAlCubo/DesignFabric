"""Tests del endpoint `/features`: reporta si el módulo de IA local está disponible."""

from __future__ import annotations

from starlette.testclient import TestClient

from designfabric.api.registry import LOCAL_AI_AVAILABLE


def test_features_reports_local_ai_state(client):
    """Las tabs de generación siempre están registradas; local_ai refleja deps reales."""
    response = client.get("/features")
    assert response.status_code == 200
    body = response.json()
    assert body["local_ai_available"] is LOCAL_AI_AVAILABLE
    assert len(body["modules"]) == 5
    assert "remove-background" in body["modules"]
    assert "scale" in body["modules"]
    assert "clearcut-batch" in body["modules"]
    assert "designfabric-batch" in body["modules"]
    assert "designfabric-single" in body["modules"]


def test_features_keeps_generation_modules_when_local_ai_flag_false(monkeypatch, tmp_path):
    """LOCAL_AI_AVAILABLE=False no oculta las tabs; solo marca deps ausentes."""
    from designfabric.api import local_ai, registry
    from designfabric.api.app import create_app
    from designfabric.api.routers import features

    monkeypatch.setattr(local_ai, "LOCAL_AI_AVAILABLE", False)
    monkeypatch.setattr(registry, "LOCAL_AI_AVAILABLE", False)
    monkeypatch.setattr(features, "LOCAL_AI_AVAILABLE", False)
    monkeypatch.setenv("DESIGNFABRIC_OUTPUT_DIR", str(tmp_path / "output"))

    app = create_app()
    with TestClient(app) as test_client:
        response = test_client.get("/features")

    assert response.status_code == 200
    body = response.json()
    assert body["local_ai_available"] is False
    assert len(body["modules"]) == 5
    assert "designfabric-batch" in body["modules"]
