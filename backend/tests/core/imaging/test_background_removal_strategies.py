"""Tests de las estrategias de eliminación de fondo."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from designfabric.core.imaging.background_remover import load_image
from designfabric.core.imaging.background_removal_strategies import (
    ColorBackgroundStrategy,
    RemovalModelPaths,
    WhiteBackgroundStrategy,
    create_background_removal_strategy,
)


def _alpha(result: np.ndarray) -> np.ndarray:
    assert result.ndim == 3 and result.shape[2] == 4
    return result[:, :, 3]


def test_white_background_strategy_masks_subject(synthetic_white_bg_path: Path) -> None:
    img = load_image(synthetic_white_bg_path)
    result = WhiteBackgroundStrategy().remove_background(img)
    alpha = _alpha(result)

    assert result.dtype == np.uint8
    assert alpha.shape == img.shape[:2]
    assert alpha[200, 200] == 255
    assert alpha[10, 10] == 0
    assert set(np.unique(alpha)).issubset({0, 255})


def test_white_background_keeps_only_largest_contour(tmp_path: Path) -> None:
    img = np.full((200, 200, 3), 255, dtype=np.uint8)
    img[40:160, 40:160] = (30, 30, 220)
    img[10:20, 10:20] = (30, 30, 220)
    path = tmp_path / "two_blobs.png"
    cv2.imwrite(str(path), img)

    alpha = _alpha(WhiteBackgroundStrategy().remove_background(load_image(path)))

    assert alpha[100, 100] == 255
    assert alpha[15, 15] == 0


def test_white_background_empty_on_full_white(tmp_path: Path) -> None:
    img = np.full((50, 50, 3), 255, dtype=np.uint8)
    path = tmp_path / "white.png"
    cv2.imwrite(str(path), img)

    alpha = _alpha(WhiteBackgroundStrategy().remove_background(load_image(path)))
    assert cv2.countNonZero(alpha) == 0


def test_color_background_strategy_masks_subject(synthetic_color_bg_path: Path) -> None:
    img = load_image(synthetic_color_bg_path)
    alpha = _alpha(ColorBackgroundStrategy().remove_background(img))

    assert alpha.dtype == np.uint8
    assert alpha.shape == img.shape[:2]
    assert alpha[200, 200] == 255
    assert alpha[10, 10] == 0


@pytest.mark.parametrize(
    "bg_bgr",
    [
        (40, 180, 40),
        (180, 40, 40),
        (40, 200, 200),
    ],
)
def test_color_background_works_with_different_backgrounds(
    tmp_path: Path, bg_bgr: tuple[int, int, int]
) -> None:
    img = np.full((400, 400, 3), bg_bgr, dtype=np.uint8)
    img[100:300, 100:300] = (30, 30, 220)
    path = tmp_path / "color.png"
    cv2.imwrite(str(path), img)

    alpha = _alpha(ColorBackgroundStrategy().remove_background(load_image(path)))

    assert alpha[200, 200] == 255
    assert alpha[10, 10] == 0


def test_create_background_removal_strategy_by_name() -> None:
    assert isinstance(create_background_removal_strategy("white_background"), WhiteBackgroundStrategy)
    assert isinstance(create_background_removal_strategy("color_background"), ColorBackgroundStrategy)


def test_create_background_removal_strategy_rejects_unknown() -> None:
    with pytest.raises(ValueError, match="Estrategia desconocida"):
        create_background_removal_strategy("unknown")  # type: ignore[arg-type]


def test_create_sam2_vitmatte_requires_model_paths() -> None:
    with pytest.raises(ValueError, match="requiere rutas"):
        create_background_removal_strategy("sam2_vitmatte")


def test_create_sam2_vitmatte_with_paths(tmp_path: Path) -> None:
    from designfabric.core.imaging.sam2_vitmatte import Sam2VitMatteStrategy

    paths = RemovalModelPaths(
        sam2_encoder_onnx=tmp_path / "sam2.encoder.onnx",
        sam2_decoder_onnx=tmp_path / "sam2.decoder.onnx",
        vitmatte_onnx=tmp_path / "vitmatte.onnx",
    )
    strategy = create_background_removal_strategy("sam2_vitmatte", model_paths=paths)
    assert isinstance(strategy, Sam2VitMatteStrategy)


def test_create_isnet_general_requires_model_paths() -> None:
    with pytest.raises(ValueError, match="requiere la ruta"):
        create_background_removal_strategy("isnet_general")


def test_create_isnet_general_with_paths(tmp_path: Path) -> None:
    from designfabric.core.imaging.isnet_strategy import IsNetGeneralStrategy

    paths = RemovalModelPaths(isnet_general_onnx=tmp_path / "isnet.onnx")
    strategy = create_background_removal_strategy("isnet_general", model_paths=paths)
    assert isinstance(strategy, IsNetGeneralStrategy)


def test_create_rembg_illustration_needs_no_model_paths() -> None:
    from designfabric.core.imaging.rembg_strategy import RembgIllustrationStrategy

    strategy = create_background_removal_strategy("rembg_illustration")
    assert isinstance(strategy, RembgIllustrationStrategy)


def test_create_birefnet_sam2_matte_needs_no_model_paths() -> None:
    from designfabric.core.imaging.birefnet_sam2_matte_strategy import BiRefNetSam2MatteStrategy

    strategy = create_background_removal_strategy("birefnet_sam2_matte")
    assert isinstance(strategy, BiRefNetSam2MatteStrategy)


def test_create_birefnet_sam2_matte_with_optional_paths(tmp_path: Path) -> None:
    from designfabric.core.imaging.birefnet_sam2_matte_strategy import BiRefNetSam2MatteStrategy

    paths = RemovalModelPaths(
        sam2_encoder_onnx=tmp_path / "sam2.encoder.onnx",
        sam2_decoder_onnx=tmp_path / "sam2.decoder.onnx",
        vitmatte_onnx=tmp_path / "vitmatte.onnx",
    )
    strategy = create_background_removal_strategy("birefnet_sam2_matte", model_paths=paths)
    assert isinstance(strategy, BiRefNetSam2MatteStrategy)
