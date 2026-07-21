"""Tests del endpoint de eliminación de fondo de ClearCut (sin mocks: CPU real, imagen sintética)."""

from __future__ import annotations

from pathlib import Path

from tests.api.conftest import wait_until


def test_strategies_endpoint_lists_known_strategies(client):
    response = client.get("/api/clearcut/strategies")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert ids == {
        "white_background",
        "color_background",
        "sam2_vitmatte",
        "isnet_general",
        "rembg_illustration",
        "birefnet_sam2_matte",
    }


def test_remove_background_job_lifecycle_reaches_succeeded(client, synthetic_white_bg_path):
    response = client.post(
        "/api/clearcut/remove-background",
        json={"input_path": str(synthetic_white_bg_path), "strategy": "white_background"},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    assert response.json()["status"] == "queued"

    def is_done():
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"}

    assert wait_until(is_done), "el recorte de una imagen sintética pequeña debería ser casi instantáneo"

    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded", final.get("error")
    result = final["result"]
    assert result["image_url"].startswith("/output/remove-background/")
    assert Path(result["output_path"]).is_file()
