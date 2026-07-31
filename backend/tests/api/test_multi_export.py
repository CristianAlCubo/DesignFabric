"""Tests del endpoint de exportación multi-tamaño de ClearCut."""

from __future__ import annotations

import zipfile
from pathlib import Path

from tests.api.conftest import make_synthetic_white_bg_image, wait_until


def test_multi_export_job_lifecycle_reaches_succeeded(client, tmp_path):
    gato = make_synthetic_white_bg_image(tmp_path / "gato.png")
    perro = make_synthetic_white_bg_image(tmp_path / "perro.png")

    response = client.post(
        "/api/clearcut/multi-export",
        json={
            "image_paths": [str(gato), str(perro)],
            "sizes": [
                {"label": "thumb", "mode": "px", "prefix": "thumb_", "width": 60},
                {"label": "half", "mode": "percent", "prefix": "half_", "percent": 50},
            ],
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    def is_done():
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"}

    assert wait_until(is_done, timeout=8.0), "2 imágenes x 2 tamaños debería resolverse rápido"

    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded", final.get("error")
    result = final["result"]
    assert result["expected"] == 4
    assert result["produced"] == 4
    assert result["zip_url"].startswith("/output/multi-export/")
    assert Path(result["zip_path"]).is_file()

    with zipfile.ZipFile(result["zip_path"]) as archive:
        names = set(archive.namelist())
        assert names == {
            "gato/thumb_gato.png",
            "gato/half_gato.png",
            "perro/thumb_perro.png",
            "perro/half_perro.png",
        }


def test_multi_export_partial_failure_reported(client, tmp_path):
    gato = make_synthetic_white_bg_image(tmp_path / "gato.png")
    missing = str(tmp_path / "no_existe.png")

    response = client.post(
        "/api/clearcut/multi-export",
        json={
            "image_paths": [str(gato), missing],
            "sizes": [{"label": "thumb", "mode": "px", "prefix": "thumb_", "width": 60}],
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    def is_done():
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"}

    assert wait_until(is_done, timeout=8.0)

    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded", final.get("error")
    result = final["result"]
    assert result["expected"] == 2
    assert result["produced"] == 1
    statuses = {item["input"]: item["status"] for item in result["items"]}
    assert statuses[str(gato)] == "succeeded"
    assert statuses[missing] == "failed"
