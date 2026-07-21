"""Tests de BiRefNetSam2MatteStrategy: BiRefNet/BRIA (rembg mockeado) + SAM2 opcional + matte."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from designfabric.core.imaging.background_removal_strategies import RemovalModelPaths
from designfabric.core.imaging.birefnet_sam2_matte_strategy import BiRefNetSam2MatteStrategy


def _square_mask(shape: tuple[int, int], box: tuple[int, int, int, int], value: int = 255) -> np.ndarray:
    y0, y1, x0, x1 = box
    mask = np.zeros(shape, dtype=np.uint8)
    mask[y0:y1, x0:x1] = value
    return mask


class _FakeSam2:
    """Devuelve una máscara centrada en el punto recibido, para probar el IoU gate."""

    def __init__(self, mask_box_size: int = 20, offset: tuple[int, int] = (0, 0)) -> None:
        self._half = mask_box_size // 2
        self._offset = offset

    def predict_masks(self, image_bgr: np.ndarray, point_xy=None) -> np.ndarray:
        h, w = image_bgr.shape[:2]
        cx, cy = point_xy if point_xy is not None else (w / 2.0, h / 2.0)
        cx += self._offset[0]
        cy += self._offset[1]
        mask = np.zeros((h, w), dtype=np.uint8)
        y0, y1 = max(0, int(cy) - self._half), min(h, int(cy) + self._half)
        x0, x1 = max(0, int(cx) - self._half), min(w, int(cx) + self._half)
        mask[y0:y1, x0:x1] = 255
        return mask[None, ...]


class _FakeVitMatte:
    def predict_alpha(self, image_bgr: np.ndarray, trimap: np.ndarray) -> np.ndarray:
        alpha = np.zeros(trimap.shape, dtype=np.float32)
        alpha[trimap == 255] = 1.0
        alpha[trimap == 128] = 0.5
        return alpha


def _patch_rembg_masks(monkeypatch: pytest.MonkeyPatch, mask_by_session: dict[str, np.ndarray]) -> None:
    def fake_new_session(name: str) -> str:
        return name

    def fake_remove(rgb: np.ndarray, *, session: str, only_mask: bool) -> np.ndarray:
        assert only_mask is True
        mask = mask_by_session[session]
        h, w = rgb.shape[:2]
        if mask.shape[:2] != (h, w):
            mask = cv2.resize(mask, (w, h), interpolation=cv2.INTER_NEAREST)
        return mask

    monkeypatch.setattr("rembg.new_session", fake_new_session)
    monkeypatch.setattr("rembg.remove", fake_remove)


def test_uses_birefnet_mask_when_sam2_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    shape = (100, 100)
    birefnet_mask = _square_mask(shape, (20, 80, 20, 80))
    _patch_rembg_masks(monkeypatch, {"birefnet-general": birefnet_mask})

    strategy = BiRefNetSam2MatteStrategy(RemovalModelPaths(), vitmatte=_FakeVitMatte())
    image = np.full((100, 100, 3), 40, dtype=np.uint8)
    result = strategy.remove_background(image)

    assert result.shape == (100, 100, 4)
    assert result[50, 50, 3] > 0
    assert result[2, 2, 3] == 0


def test_sam2_refinement_adopted_when_iou_is_high(monkeypatch: pytest.MonkeyPatch) -> None:
    shape = (200, 200)
    birefnet_mask = _square_mask(shape, (60, 140, 60, 140))
    _patch_rembg_masks(monkeypatch, {"birefnet-general": birefnet_mask})

    # SAM2 devuelve un cuadrado ligeramente distinto pero con alto solape (mismo centro).
    sam2 = _FakeSam2(mask_box_size=76, offset=(0, 0))
    strategy = BiRefNetSam2MatteStrategy(RemovalModelPaths(), sam2=sam2, vitmatte=_FakeVitMatte())
    image = np.full((200, 200, 3), 40, dtype=np.uint8)
    result = strategy.remove_background(image)

    assert result.shape == (200, 200, 4)
    assert result[100, 100, 3] > 0


def test_sam2_refinement_rejected_when_iou_is_low(monkeypatch: pytest.MonkeyPatch) -> None:
    shape = (200, 200)
    birefnet_mask = _square_mask(shape, (60, 140, 60, 140))
    _patch_rembg_masks(monkeypatch, {"birefnet-general": birefnet_mask})

    # SAM2 devuelve una máscara pequeña y desplazada: bajo IoU, debe descartarse.
    sam2 = _FakeSam2(mask_box_size=10, offset=(80, 80))
    strategy = BiRefNetSam2MatteStrategy(RemovalModelPaths(), sam2=sam2, vitmatte=_FakeVitMatte())
    image = np.full((200, 200, 3), 40, dtype=np.uint8)
    result = strategy.remove_background(image)

    # Se conserva la máscara de BiRefNet (centro sigue siendo sujeto).
    assert result[100, 100, 3] > 0


def test_uses_bria_matte_when_vitmatte_not_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    shape = (100, 100)
    birefnet_mask = _square_mask(shape, (20, 80, 20, 80))
    bria_alpha = np.full(shape, 220, dtype=np.uint8)
    _patch_rembg_masks(
        monkeypatch,
        {"birefnet-general": birefnet_mask, "bria-rmbg": bria_alpha},
    )

    strategy = BiRefNetSam2MatteStrategy(RemovalModelPaths())
    image = np.full((100, 100, 3), 40, dtype=np.uint8)
    result = strategy.remove_background(image)

    assert result.shape == (100, 100, 4)
    assert result[50, 50, 3] > 0
    # Fuera de la región detectada por BiRefNet, BRIA queda acotado a 0 (con margen de dilatación).
    assert result[2, 2, 3] == 0


def test_empty_mask_returns_transparent_image(monkeypatch: pytest.MonkeyPatch) -> None:
    shape = (50, 50)
    _patch_rembg_masks(monkeypatch, {"birefnet-general": np.zeros(shape, dtype=np.uint8)})

    strategy = BiRefNetSam2MatteStrategy(RemovalModelPaths(), vitmatte=_FakeVitMatte())
    image = np.full((50, 50, 3), 200, dtype=np.uint8)
    result = strategy.remove_background(image)

    assert result.shape == (50, 50, 4)
    assert np.count_nonzero(result[:, :, 3]) == 0
