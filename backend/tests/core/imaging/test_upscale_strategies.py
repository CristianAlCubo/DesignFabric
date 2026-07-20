"""Tests del patrón Strategy de escalado y factor inteligente."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from designfabric.core.imaging.ai_upscalers.common import choose_model_scale_factor, resolve_target_size
from designfabric.core.imaging.upscale_config import UpscaleConfig, load_upscale_config
from designfabric.core.imaging.upscale_pipeline import scale_image
from designfabric.core.imaging.upscale_strategies import (
    RealEsrganUpscaleStrategy,
    UpscaleError,
    UpscaleRequest,
    UpscaleResult,
    UpscaleStrategy,
    create_upscale_strategy,
)


def _make_bgra(size: int = 64) -> np.ndarray:
    img = np.zeros((size, size, 4), dtype=np.uint8)
    margin = size // 5
    img[margin : size - margin, margin : size - margin] = (30, 30, 220, 255)
    return img


def _make_png(path: Path, size: int = 64) -> Path:
    ok, buf = cv2.imencode(".png", _make_bgra(size))
    assert ok
    path.write_bytes(buf.tobytes())
    return path


def _request(
    image: np.ndarray,
    *,
    target_width: int | None = 128,
    target_height: int | None = 128,
    suffix: str = ".png",
    config: UpscaleConfig | None = None,
) -> UpscaleRequest:
    ok, buf = cv2.imencode(".png", image)
    assert ok
    return UpscaleRequest(
        image_bgra=image,
        png_bytes=buf.tobytes(),
        input_suffix=suffix,
        target_width=target_width,
        target_height=target_height,
        config=config or UpscaleConfig(),
    )


class FakeBackend:
    native_scale = 4

    def upscale_to_factor(self, image_bgra: np.ndarray, factor: int) -> np.ndarray:
        h, w = image_bgra.shape[:2]
        return cv2.resize(image_bgra, (w * factor, h * factor), interpolation=cv2.INTER_NEAREST)


def test_create_upscale_strategy_known_ids() -> None:
    strategy = create_upscale_strategy("realesrgan")
    assert strategy.name == "realesrgan"


def test_create_upscale_strategy_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="desconocida"):
        create_upscale_strategy("auto")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="desconocida"):
        create_upscale_strategy("vector")  # type: ignore[arg-type]


def test_choose_model_scale_factor_thresholds() -> None:
    assert choose_model_scale_factor(1000, 1000, 800, 800) == 1
    assert choose_model_scale_factor(100, 100, 180, 180) == 2
    assert choose_model_scale_factor(50, 50, 200, 200) == 4
    assert choose_model_scale_factor(50, 50, 200, 200, max_scale_factor=2) == 2


def test_resolve_target_size_aspect() -> None:
    assert resolve_target_size(100, 50, 200, None) == (200, 100)
    assert resolve_target_size(100, 50, None, 100) == (200, 100)


def test_pipeline_passthrough_when_all_fail(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from designfabric.core.imaging import upscale_pipeline as pipeline

    input_path = _make_png(tmp_path / "in.png", size=48)
    output_path = tmp_path / "out.png"
    original = input_path.read_bytes()

    class _AlwaysFail(UpscaleStrategy):
        name = "realesrgan"

        def upscale(self, request: UpscaleRequest) -> UpscaleResult:
            raise UpscaleError("boom-esrgan")

    monkeypatch.setattr(pipeline, "create_upscale_strategy", lambda name: _AlwaysFail())

    outcome = scale_image(
        input_path,
        output_path,
        strategy="realesrgan",
        strategy_impl=_AlwaysFail(),
    )
    assert outcome.result.backend == "passthrough"
    assert outcome.result.warning is not None
    assert output_path.read_bytes() == original


def test_scale_image_realesrgan_with_fake_backend(tmp_path: Path) -> None:
    input_path = _make_png(tmp_path / "in.png")
    output_path = tmp_path / "out.png"
    outcome = scale_image(
        input_path,
        output_path,
        strategy="realesrgan",
        width=80,
        height=80,
        strategy_impl=RealEsrganUpscaleStrategy(backend=FakeBackend()),  # type: ignore[arg-type]
    )
    assert outcome.output_path == output_path
    loaded = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
    assert loaded is not None
    assert loaded.shape == (80, 80, 4)


def test_load_upscale_config_from_toml(tmp_path: Path) -> None:
    config_path = tmp_path / "clearcut.toml"
    config_path.write_text(
        "[upscale]\nmax_scale_factor = 2\nmodels_dir = 'custom-models'\n",
        encoding="utf-8",
    )
    cfg = load_upscale_config(config_path)
    assert cfg.max_scale_factor == 2
    assert cfg.models_dir == "custom-models"
    assert cfg.cpu_backend == "realesrgan"


def test_realesrgan_strategy_uses_injected_backend() -> None:
    result = RealEsrganUpscaleStrategy(backend=FakeBackend()).upscale(  # type: ignore[arg-type]
        _request(_make_bgra(32), target_width=128, target_height=128)
    )
    assert result.backend == "realesrgan"
    assert result.device == "cpu"
    assert result.scale_factor == 4.0


@pytest.mark.integration
def test_realesrgan_integration_if_model_present() -> None:
    model = Path(".local/models/realesr-general-x4v3.onnx")
    if not model.is_file():
        pytest.skip("Modelo Real-ESRGAN no presente")
    pytest.importorskip("onnxruntime")
    from designfabric.core.imaging.ai_upscalers.realesrgan import RealEsrganBackend

    backend = RealEsrganBackend(model)
    out = backend.upscale_to_factor(_make_bgra(32), 4)
    assert out.shape[0] == 128
    assert out.shape[1] == 128
