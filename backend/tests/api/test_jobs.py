"""Tests de los endpoints de jobs de generación IA, con el pipeline mockeado (ver `conftest.py`)."""

from __future__ import annotations

import time

import pytest

from designfabric.api.registry import LOCAL_AI_AVAILABLE
from tests.api.conftest import wait_until

pytestmark = pytest.mark.skipif(
    not LOCAL_AI_AVAILABLE, reason="requiere el extra local-ai (endpoints /api/jobs/batch y /api/jobs/single-image)"
)


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_batch_job_lifecycle_reaches_succeeded(client):
    response = client.post("/api/jobs/batch", json={"num_images": 1})
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert response.json()["status"] == "queued"

    def is_done():
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"}

    assert wait_until(is_done), "el job mockeado debería resolverse casi instantáneamente"

    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded"
    assert final["result"]["failure_count"] == 0
    assert final["result"]["results"][0]["image_url"] == "/output/fake/sticker_1_x.png"


def test_batch_job_rejects_invalid_num_images(client):
    response = client.post("/api/jobs/batch", json={"num_images": 0})
    assert response.status_code == 422


def test_single_image_job_lifecycle_reaches_succeeded(client):
    response = client.post("/api/jobs/single-image", json={"prompt": "a lone wolf howling"})
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    def is_done():
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"}

    assert wait_until(is_done)
    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded"
    assert final["result"]["prompt"] == "a fake prompt"


def test_get_unknown_job_returns_404(client):
    response = client.get("/api/jobs/does-not-exist")
    assert response.status_code == 404


def test_list_jobs_returns_most_recent_first(client):
    first = client.post("/api/jobs/batch", json={"num_images": 1}).json()["job_id"]
    second = client.post("/api/jobs/batch", json={"num_images": 1}).json()["job_id"]

    listing = client.get("/api/jobs").json()
    ids = [job["id"] for job in listing]
    assert ids.index(second) < ids.index(first)


def test_cancel_queued_job_succeeds(client, mocker):
    # Ocupamos al worker con un primer job lento para que el segundo quede QUEUED
    # el tiempo suficiente como para poder cancelarlo antes de que se procese.
    mocker.patch(
        "designfabric.api.routers.batch_generation.run_batch",
        side_effect=lambda *a, **k: time.sleep(0.3) or None,
    )

    busy_job = client.post("/api/jobs/batch", json={"num_images": 1}).json()["job_id"]
    queued_job = client.post("/api/jobs/batch", json={"num_images": 1}).json()["job_id"]

    assert wait_until(lambda: client.get(f"/api/jobs/{busy_job}").json()["status"] == "running")
    assert client.get(f"/api/jobs/{queued_job}").json()["status"] == "queued"

    cancel_response = client.delete(f"/api/jobs/{queued_job}")
    assert cancel_response.status_code == 204
    assert client.get(f"/api/jobs/{queued_job}").json()["status"] == "cancelled"


def test_cancel_finished_job_returns_409(client):
    job_id = client.post("/api/jobs/batch", json={"num_images": 1}).json()["job_id"]
    assert wait_until(lambda: client.get(f"/api/jobs/{job_id}").json()["status"] == "succeeded")

    response = client.delete(f"/api/jobs/{job_id}")
    assert response.status_code == 409


def test_progress_websocket_accepts_connection(client):
    job_id = client.post("/api/jobs/batch", json={"num_images": 1}).json()["job_id"]
    with client.websocket_connect(f"/api/jobs/{job_id}/ws"):
        pass  # conectar y desconectar sin error ya valida el ciclo de suscripción/desuscripción
