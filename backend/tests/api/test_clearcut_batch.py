"""Tests del endpoint de batch de ClearCut (sin mocks: CPU real, imágenes sintéticas).

`scale_strategy="vector"` para no depender del modelo ONNX de Real-ESRGAN
(ver `test_scale.py` para la misma razón).
"""

from __future__ import annotations

from pathlib import Path

from tests.api.conftest import make_synthetic_white_bg_image, wait_until


def test_clearcut_batch_job_lifecycle_reaches_succeeded(client, tmp_path):
    input_dir = tmp_path / "batch_input"
    input_dir.mkdir()
    make_synthetic_white_bg_image(input_dir / "one.png")
    make_synthetic_white_bg_image(input_dir / "two.png")

    output_dir = tmp_path / "batch_output"

    response = client.post(
        "/api/clearcut/batch",
        json={
            "input": {"kind": "folder", "directory": str(input_dir)},
            "output_dir": str(output_dir),
            "removal_strategy": "white_background",
            "scale_strategy": "vector",
            "factor": 2,
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    def is_done():
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"}

    assert wait_until(is_done, timeout=8.0), "un lote de 2 imágenes sintéticas debería resolverse rápido"

    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded", final.get("error")
    result = final["result"]
    assert result["total"] == 2
    assert result["succeeded"] == 2
    assert result["failed"] == 0
    assert result["cancelled"] is False
    for item in result["items"]:
        assert item["status"] == "succeeded"
        assert Path(item["output"]).is_file()
