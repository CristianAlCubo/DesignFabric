"""Tests de las estrategias de detección de silueta."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from designfabricv2.core.imaging.background_remover import load_image
from designfabricv2.core.imaging.silhouette_strategies import (
    ColorBackgroundStrategy,
    WhiteBackgroundStrategy,
    create_silhouette_strategy,
)


def test_white_background_strategy_masks_subject(synthetic_white_bg_path: Path) -> None:
    img = load_image(synthetic_white_bg_path)
    mask = WhiteBackgroundStrategy().generate_mask(img)

    assert mask.dtype == np.uint8
    assert mask.shape == img.shape[:2]
    assert mask[200, 200] == 255
    assert mask[10, 10] == 0
    assert set(np.unique(mask)).issubset({0, 255})


def test_white_background_keeps_only_largest_contour(tmp_path: Path) -> None:
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    img[40:160, 40:160] = (30, 30, 220)
    img[10:20, 10:20] = (30, 30, 220)
    path = tmp_path / "two_blobs.png"
    cv2.imwrite(str(path), img)

    mask = WhiteBackgroundStrategy().generate_mask(load_image(path))

    assert mask[100, 100] == 255
    assert mask[15, 15] == 0


def test_white_background_empty_on_full_white(tmp_path: Path) -> None:
    img = np.full((50, 50, 3), 255, dtype=np.uint8)
    path = tmp_path / "white.png"
    cv2.imwrite(str(path), img)

    mask = WhiteBackgroundStrategy().generate_mask(load_image(path))
    assert cv2.countNonZero(mask) == 0


def test_color_background_strategy_masks_subject(synthetic_color_bg_path: Path) -> None:
    img = load_image(synthetic_color_bg_path)
    mask = ColorBackgroundStrategy().generate_mask(img)

    assert mask.dtype == np.uint8
    assert mask.shape == img.shape[:2]
    assert mask[200, 200] == 255
    assert mask[10, 10] == 0


@pytest.mark.parametrize(
    "bg_bgr",
    [
        (40, 180, 40),   # verde
        (180, 40, 40),   # azul
        (40, 200, 200),  # amarillo
    ],
)
def test_color_background_works_with_different_backgrounds(
    tmp_path: Path, bg_bgr: tuple[int, int, int]
) -> None:
    img = np.full((400, 400, 3), bg_bgr, dtype=np.uint8)
    img[100:300, 100:300] = (30, 30, 220)
    path = tmp_path / "color.png"
    cv2.imwrite(str(path), img)

    mask = ColorBackgroundStrategy().generate_mask(load_image(path))

    assert mask[200, 200] == 255
    assert mask[10, 10] == 0


def test_create_silhouette_strategy_by_name() -> None:
    assert isinstance(create_silhouette_strategy("white_background"), WhiteBackgroundStrategy)
    assert isinstance(create_silhouette_strategy("color_background"), ColorBackgroundStrategy)


def test_create_silhouette_strategy_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Estrategia desconocida"):
        create_silhouette_strategy("unknown")  # type: ignore[arg-type]
