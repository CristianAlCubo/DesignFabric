"""Tests del endpoint de escalado de ClearCut.

Real-ESRGAN se mockea con un backend de resize (sin modelo ONNX) para CI.
"""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from designfabric.core.imaging.upscale_strategies import RealEsrganUpscaleStrategy
from tests.api.conftest import wait_until


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


def test_scale_defaults_endpoint(client):
    response = client.get("/api/clearcut/scale/defaults")
    assert response.status_code == 200
    body = response.json()
    assert body["default_strategy"] == "realesrgan"
    assert {item["id"] for item in body["strategies"]} == {"realesrgan"}
    assert "trace" not in body
    assert "dpi" not in body


def test_scale_job_lifecycle_reaches_succeeded(client, synthetic_white_bg_path):
    response = client.post(
        "/api/clearcut/scale",
        json={
            "input_path": str(synthetic_white_bg_path),
            "strategy": "realesrgan",
            "width": 240,
            "height": 240,
        },
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    def is_done():
        return client.get(f"/api/jobs/{job_id}").json()["status"] in {"succeeded", "failed"}

    assert wait_until(is_done, timeout=8.0), "el escalado mockeado debería ser rápido"

    final = client.get(f"/api/jobs/{job_id}").json()
    assert final["status"] == "succeeded", final.get("error")
    result = final["result"]
    assert result["backend"] == "realesrgan"
    assert result["image_url"].startswith("/output/scale/")
    assert Path(result["output_path"]).is_file()
