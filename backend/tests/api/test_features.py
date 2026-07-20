"""Tests del endpoint `/features`: reporta si el módulo de IA local está disponible."""

from __future__ import annotations

from starlette.testclient import TestClient

from designfabricv2.api.registry import LOCAL_AI_AVAILABLE


def test_features_reports_local_ai_state(client):
    """En el entorno normal de test, refleja lo que haya realmente instalado (con o sin `local-ai`)."""
    response = client.get("/features")
    assert response.status_code == 200
    body = response.json()
    assert body["local_ai_available"] is LOCAL_AI_AVAILABLE
    expected_count = 5 if LOCAL_AI_AVAILABLE else 3
    assert len(body["modules"]) == expected_count
    assert "remove-background" in body["modules"]
    assert "scale" in body["modules"]
    assert "clearcut-batch" in body["modules"]


def test_features_reports_unavailable_when_local_ai_missing(monkeypatch, tmp_path):
    """Simula el entorno sin el extra `local-ai`: solo deberían quedar los 3 módulos CPU."""
    from designfabricv2.api import registry
    from designfabricv2.api.app import create_app
    from designfabricv2.api.routers import features

    cpu_only = tuple(m for m in registry.FEATURE_REGISTRY if m.worker_affinity == "cpu")

    # `features.py` y `app.py` importaron `FEATURE_REGISTRY`/`LOCAL_AI_AVAILABLE` con
    # `from ... import`, así que quedan como nombres propios de cada módulo: hay que
    # parchear esas referencias ya bindeadas, no solo las de `registry`.
    monkeypatch.setattr(registry, "LOCAL_AI_AVAILABLE", False)
    monkeypatch.setattr(registry, "FEATURE_REGISTRY", cpu_only)
    monkeypatch.setattr(features, "LOCAL_AI_AVAILABLE", False)
    monkeypatch.setattr(features, "FEATURE_REGISTRY", cpu_only)
    monkeypatch.setattr("designfabricv2.api.app.FEATURE_REGISTRY", cpu_only)
    monkeypatch.setenv("DESIGNFABRIC_OUTPUT_DIR", str(tmp_path / "output"))

    app = create_app()
    with TestClient(app) as test_client:
        response = test_client.get("/features")

    assert response.status_code == 200
    body = response.json()
    assert body["local_ai_available"] is False
    assert set(body["modules"]) == {"remove-background", "scale", "clearcut-batch"}
