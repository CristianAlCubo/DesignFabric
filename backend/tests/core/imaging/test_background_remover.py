"""Tests unitarios y end-to-end del pipeline de eliminación de fondo."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from designfabric.core.imaging.background_removal_ops import apply_mask, iterative_erode
from designfabric.core.imaging.background_remover import (
    BackgroundRemover,
    RemovalConfig,
    load_image,
    process_image,
    save_image,
)
from designfabric.core.imaging.background_removal_strategies import (
    ColorBackgroundStrategy,
    WhiteBackgroundStrategy,
)


def test_load_image_returns_bgr(synthetic_white_bg_path: Path) -> None:
    image = load_image(synthetic_white_bg_path)
    assert image.ndim == 3
    assert image.shape[2] == 3
    assert image.dtype == np.uint8


def test_load_image_rejects_unsupported_format(tmp_path: Path) -> None:
    bad_file = tmp_path / "image.bmp"
    bad_file.write_bytes(b"not a real bmp")
    with pytest.raises(ValueError, match="Formato no soportado"):
        load_image(bad_file)


def test_load_image_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_image(tmp_path / "does_not_exist.png")


def test_load_image_unreadable_file_raises(tmp_path: Path) -> None:
    broken = tmp_path / "broken.png"
    broken.write_bytes(b"not-a-png")
    with pytest.raises(ValueError, match="No se pudo leer"):
        load_image(broken)


def test_iterative_erode_reduces_or_stabilizes_area() -> None:
    mask = np.zeros((100, 100), dtype=np.uint8)
    mask[20:80, 20:80] = 255
    eroded = iterative_erode(mask, max_iterations=5)

    assert eroded.shape == mask.shape
    assert cv2.countNonZero(eroded) <= cv2.countNonZero(mask)
    assert cv2.countNonZero(eroded) > 0


def test_iterative_erode_stops_when_stable() -> None:
    mask = np.zeros((50, 50), dtype=np.uint8)
    mask[10:40, 10:40] = 255
    eroded = iterative_erode(mask, max_iterations=1)
    assert cv2.countNonZero(eroded) > 0


def test_iterative_erode_empty_mask_stays_empty() -> None:
    mask = np.zeros((20, 20), dtype=np.uint8)
    eroded = iterative_erode(mask, max_iterations=5)
    assert cv2.countNonZero(eroded) == 0


def test_iterative_erode_does_not_wipe_thin_subject() -> None:
    mask = np.zeros((30, 30), dtype=np.uint8)
    mask[14:16, 5:25] = 255
    eroded = iterative_erode(mask, max_iterations=5)
    assert cv2.countNonZero(eroded) > 0


def test_apply_mask_produces_bgra() -> None:
    img = np.zeros((10, 10, 3), dtype=np.uint8)
    img[:, :] = (10, 20, 30)
    mask = np.full((10, 10), 255, dtype=np.uint8)
    result = apply_mask(img, mask)

    assert result.shape == (10, 10, 4)
    assert np.array_equal(result[:, :, 0], img[:, :, 0])
    assert np.array_equal(result[:, :, 1], img[:, :, 1])
    assert np.array_equal(result[:, :, 2], img[:, :, 2])
    assert np.array_equal(result[:, :, 3], mask)


def test_save_image_creates_parent_dirs(tmp_path: Path) -> None:
    output = tmp_path / "nested" / "out" / "result.png"
    image = np.zeros((8, 8, 4), dtype=np.uint8)
    image[:, :, 3] = 255

    save_image(image, output)

    assert output.is_file()
    loaded = cv2.imread(str(output), cv2.IMREAD_UNCHANGED)
    assert loaded is not None
    assert loaded.shape == (8, 8, 4)


def test_processor_set_strategy_switches_behavior(
    synthetic_white_bg_path: Path,
    synthetic_color_bg_path: Path,
    tmp_path: Path,
) -> None:
    processor = BackgroundRemover(WhiteBackgroundStrategy())
    out_white = tmp_path / "white.png"
    result_white = processor.process(synthetic_white_bg_path, out_white)
    assert out_white.is_file()
    assert result_white[200, 200, 3] == 255

    processor.set_strategy(ColorBackgroundStrategy())
    out_color = tmp_path / "color.png"
    result_color = processor.process(synthetic_color_bg_path, out_color)
    assert out_color.is_file()
    assert result_color[200, 200, 3] == 255
    assert result_color[10, 10, 3] == 0


def test_process_image_preserves_subject_rgb(
    synthetic_white_bg_path: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "out.png"
    result = process_image(
        synthetic_white_bg_path,
        output_path,
        WhiteBackgroundStrategy(),
        RemovalConfig(),
    )

    assert tuple(result[200, 200, :3]) == (30, 30, 220)
    assert result[200, 200, 3] == 255
    assert result[10, 10, 3] == 0


def test_process_image_end_to_end_white_background(
    synthetic_white_bg_path: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "out.png"
    result = process_image(
        synthetic_white_bg_path,
        output_path,
        WhiteBackgroundStrategy(),
        RemovalConfig(),
    )

    assert output_path.is_file()
    assert result.shape[2] == 4
    alpha = result[:, :, 3]
    assert alpha.max() > 0
    assert alpha[10, 10] == 0
    assert alpha[200, 200] == 255

    reloaded = cv2.imread(str(output_path), cv2.IMREAD_UNCHANGED)
    assert reloaded is not None
    assert reloaded.shape[2] == 4


def test_process_image_end_to_end_color_background(
    synthetic_color_bg_path: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "out.png"
    result = process_image(
        synthetic_color_bg_path,
        output_path,
        ColorBackgroundStrategy(),
        RemovalConfig(),
    )

    assert output_path.is_file()
    alpha = result[:, :, 3]
    assert alpha[10, 10] == 0
    assert alpha[200, 200] == 255


def test_process_image_with_real_cat_asset(cat_asset_path: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "cat_out.png"
    result = process_image(cat_asset_path, output_path, WhiteBackgroundStrategy())

    assert output_path.is_file()
    assert result.shape[2] == 4
    assert result[:, :, 3].max() == 255
    assert result[:, :, 3].min() == 0


def test_process_image_with_real_sticker_asset(
    sticker_asset_path: Path, tmp_path: Path
) -> None:
    output_path = tmp_path / "sticker_out.png"
    result = process_image(sticker_asset_path, output_path, ColorBackgroundStrategy())

    assert output_path.is_file()
    assert result.shape[2] == 4
    assert result[:, :, 3].max() == 255
    assert result[:, :, 3].min() == 0
