"""Tests del endpoint de batch de ClearCut.

Real-ESRGAN se mockea con un backend de resize (sin modelo ONNX) para CI.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from designfabric.core.imaging.upscale_strategies import RealEsrganUpscaleStrategy
from tests.api.conftest import make_synthetic_white_bg_image, wait_until


class _FakeBackend:
    native_scale = 4

    def upscale_to_factor(self, image_bgra: np.ndarray, factor: int) -> np.ndarray:
        h, w = image_bgra.shape[:2]
        return cv2.resize(image_bgra, (w * factor, h * factor), interpolation=cv2.INTER_NEAREST)


@pytest.fixture(autouse=True)
def _mock_realesrgan(monkeypatch: pytest.MonkeyPatch) -> None:
    fake = RealEsrganUpscaleStrategy(backend=_FakeBackend())  # type: ignore[arg-type]
    monkeypatch.setattr(
        "designfabric.core.imaging.upscale_pipeline.create_upscale_strategy",
        lambda name: fake,
    )
    monkeypatch.setattr(
        "designfabric.core.imaging.upscale_pipeline.ensure_models_for_strategy",
        lambda *args, **kwargs: None,
    )


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
            "scale_strategy": "realesrgan",
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
