"""Jobs con providers test reales (sin mock del pipeline, sin local-ai)."""

from __future__ import annotations

from pathlib import Path

import pytest
from starlette.testclient import TestClient

from designfabric.api.app import create_app
from designfabric.core.generation.image_providers import _test_sticker_path
from tests.api.conftest import wait_until


@pytest.fixture
def live_client(tmp_path, monkeypatch) -> TestClient:
    monkeypatch.setenv("DESIGNFABRIC_OUTPUT_DIR", str(tmp_path / "output"))
    monkeypatch.setenv("CLEARCUT_SKIP_MODEL_DOWNLOAD", "1")
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def test_batch_job_with_real_test_providers(live_client):
    response = live_client.post(
        "/api/jobs/batch",
        json={"num_images": 1, "llm_provider": "test", "image_provider": "test"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    assert wait_until(
        lambda: live_client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"},
        timeout=10.0,
    )
    final = live_client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded"
    filename = final["result"]["results"][0]["filename"]
    assert filename is not None
    assert Path(filename).read_bytes() == _test_sticker_path().read_bytes()


def test_single_image_job_with_real_test_provider(live_client):
    response = live_client.post(
        "/api/jobs/single-image",
        json={"prompt": "hello world", "apply_style_suffix": False, "image_provider": "test"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    assert wait_until(
        lambda: live_client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"},
        timeout=10.0,
    )
    final = live_client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded"
    assert final["result"]["prompt"] == "hello world"
    assert Path(final["result"]["filename"]).read_bytes() == _test_sticker_path().read_bytes()
