"""Tests del motor de escalado VectorEngine."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from designfabric.core.imaging.vector_engine import (
    ExportConfig,
    TraceConfig,
    VectorEngine,
    VectorEngineError,
    get_scale_defaults,
    scale_image,
)


def _make_rgba_png_bytes(size: int = 64) -> bytes:
    img = np.zeros((size, size, 4), dtype=np.uint8)
    margin = size // 5
    img[margin : size - margin, margin : size - margin] = (30, 30, 220, 255)
    ok, buf = cv2.imencode(".png", img)
    assert ok
    return buf.tobytes()


def test_get_scale_defaults_matches_dataclasses() -> None:
    defaults = get_scale_defaults()
    assert defaults["dpi"] == ExportConfig().dpi
    assert defaults["trace"]["corner_threshold"] == TraceConfig().corner_threshold
    assert defaults["trace"]["color_precision"] == TraceConfig().color_precision


def test_vectorize_returns_svg() -> None:
    engine = VectorEngine()
    svg = engine.vectorize(_make_rgba_png_bytes())
    assert "<svg" in svg
    assert "path" in svg.lower()


def test_process_preserves_alpha_and_honors_size() -> None:
    engine = VectorEngine()
    png = engine.process(_make_rgba_png_bytes(), ExportConfig(width_px=128, height_px=128))
    arr = np.frombuffer(png, dtype=np.uint8)
    decoded = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    assert decoded is not None
    assert decoded.shape == (128, 128, 4)
    assert int(decoded[..., 3].max()) == 255
    assert int(decoded[..., 3].min()) == 0


def test_process_dpi_scales_above_source() -> None:
    engine = VectorEngine()
    source_size = 40
    png = engine.process(
        _make_rgba_png_bytes(source_size),
        ExportConfig(dpi=192.0),
    )
    decoded = cv2.imdecode(np.frombuffer(png, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    assert decoded is not None
    assert decoded.shape[0] >= source_size * 2 - 1
    assert decoded.shape[1] >= source_size * 2 - 1


def test_vectorize_rejects_non_png() -> None:
    engine = VectorEngine()
    with pytest.raises(VectorEngineError, match="PNG válido"):
        engine.vectorize(b"not-a-png")


def test_trace_config_validates_length_threshold() -> None:
    with pytest.raises(VectorEngineError, match="length_threshold"):
        TraceConfig(length_threshold=2.0).validated()


def test_scale_image_writes_output(tmp_path: Path) -> None:
    input_path = tmp_path / "in.png"
    output_path = tmp_path / "out.png"
    input_path.write_bytes(_make_rgba_png_bytes())

    result = scale_image(
        input_path,
        output_path,
        export=ExportConfig(width_px=100, height_px=100),
    )

    assert result == output_path
    assert output_path.is_file()
    loaded = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
    assert loaded is not None
    assert loaded.shape == (100, 100, 4)


def test_scale_image_rejects_non_png_extension(tmp_path: Path) -> None:
    input_path = tmp_path / "in.jpeg"
    input_path.write_bytes(_make_rgba_png_bytes())
    with pytest.raises(VectorEngineError, match="PNG"):
        scale_image(input_path, tmp_path / "out.png")
