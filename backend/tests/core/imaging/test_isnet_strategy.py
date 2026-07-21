"""Tests de la estrategia IS-Net (general-use), con sesión ONNX fake."""

from __future__ import annotations

import numpy as np

from designfabric.core.imaging.isnet_strategy import IsNetGeneralStrategy


class _Meta:
    def __init__(self, name: str) -> None:
        self.name = name


class _FakeSession:
    """Sesión ONNX fake: devuelve un mapa de saliencia con un cuadrado central."""

    def __init__(self) -> None:
        self._input_name = "input.1"

    def get_inputs(self) -> list[_Meta]:
        return [_Meta(self._input_name)]

    def run(self, output_names, feeds):
        del output_names
        nchw = feeds[self._input_name]
        assert nchw.shape == (1, 3, 1024, 1024)
        assert nchw.dtype == np.float32

        pred = np.full((1024, 1024), -2.0, dtype=np.float32)
        pred[256:768, 256:768] = 3.0
        return [pred[None, None, ...]]


def _make_strategy() -> IsNetGeneralStrategy:
    strategy = IsNetGeneralStrategy.__new__(IsNetGeneralStrategy)
    strategy._session = _FakeSession()  # type: ignore[attr-defined]
    return strategy


def test_isnet_preprocess_resizes_to_1024_and_normalizes() -> None:
    strategy = _make_strategy()
    image = np.full((300, 500, 3), 128, dtype=np.uint8)
    result = strategy.remove_background(image)
    assert result.shape == (300, 500, 4)
    assert result.dtype == np.uint8


def test_isnet_alpha_marks_foreground_and_background() -> None:
    strategy = _make_strategy()
    image = np.full((200, 200, 3), 128, dtype=np.uint8)
    result = strategy.remove_background(image)

    alpha = result[:, :, 3]
    # Centro (cuadrado de alta activación en el fake) → alpha alto.
    assert alpha[100, 100] > 200
    # Esquina (activación mínima en el fake) → alpha bajo.
    assert alpha[2, 2] < 50


def test_isnet_extract_prediction_handles_flat_output() -> None:
    flat = np.full((1, 1, 8, 8), 0.5, dtype=np.float32)
    pred = IsNetGeneralStrategy._extract_prediction([flat])
    assert pred.shape == (8, 8)
    assert np.all(pred == 0.0)


def test_isnet_missing_model_raises_clear_error(tmp_path) -> None:
    strategy = IsNetGeneralStrategy(tmp_path / "missing.onnx")
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    try:
        strategy.remove_background(image)
    except RuntimeError as exc:
        assert "Modelo IS-Net no encontrado" in str(exc)
    else:
        raise AssertionError("Se esperaba RuntimeError por modelo faltante")
