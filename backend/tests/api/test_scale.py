"""Tests del endpoint de escalado de ClearCut (sin mocks: CPU real, imagen sintética).

Se usa la estrategia `vector` (VTracer + CairoSVG) en vez de `realesrgan`
para no depender de que el modelo ONNX esté descargado en la máquina de
CI/desarrollo (`CLEARCUT_SKIP_MODEL_DOWNLOAD=1` ya lo desactiva por defecto
vía el conftest de esta suite).
"""

from __future__ import annotations

from pathlib import Path

from tests.api.conftest import wait_until


def test_scale_defaults_endpoint(client):
    response = client.get("/api/clearcut/scale/defaults")
    assert response.status_code == 200
    body = response.json()
    assert body["default_strategy"] == "realesrgan"
    assert {item["id"] for item in body["strategies"]} == {"vector", "realesrgan"}
    assert "trace" in body


def test_scale_job_lifecycle_reaches_succeeded(client, synthetic_white_bg_path):
    response = client.post(
        "/api/clearcut/scale",
        json={"input_path": str(synthetic_white_bg_path), "strategy": "vector", "width": 240, "height": 240},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    def is_done():
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"}

    assert wait_until(is_done, timeout=8.0), "el escalado vectorial de una imagen pequeña debería ser rápido"

    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded", final.get("error")
    result = final["result"]
    assert result["backend"] == "vector"
    assert result["image_url"].startswith("/output/scale/")
    assert Path(result["output_path"]).is_file()
