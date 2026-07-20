"""Fixtures compartidas para los tests de ClearCut."""

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

SAMPLES_INPUT = Path(__file__).resolve().parents[4] / "samples" / "input"


@pytest.fixture(autouse=True)
def _skip_model_downloads_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    """Evita descargas de red en la suite unitaria salvo tests que lo anulen."""
    monkeypatch.setenv("CLEARCUT_SKIP_MODEL_DOWNLOAD", "1")


def make_synthetic_white_bg_image(path: Path) -> Path:
    """Genera un PNG de 400x400: fondo blanco sólido y un cuadrado rojo centrado."""
    img = np.full((400, 400, 3), 255, dtype=np.uint8)
    img[100:300, 100:300] = (30, 30, 220)  # BGR rojo
    cv2.imwrite(str(path), img)
    return path


def make_synthetic_color_bg_image(path: Path, bg_bgr: tuple[int, int, int] = (40, 180, 40)) -> Path:
    """Genera un PNG de 400x400: fondo de color y un cuadrado rojo centrado."""
    img = np.full((400, 400, 3), bg_bgr, dtype=np.uint8)
    img[100:300, 100:300] = (30, 30, 220)  # BGR rojo
    cv2.imwrite(str(path), img)
    return path


@pytest.fixture(scope="session")
def synthetic_white_bg_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Imagen sintética con fondo blanco para toda la sesión de tests."""
    directory = tmp_path_factory.mktemp("clearcut_synthetic_white")
    return make_synthetic_white_bg_image(directory / "synthetic_white.png")


@pytest.fixture(scope="session")
def synthetic_color_bg_path(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Imagen sintética con fondo verde para toda la sesión de tests."""
    directory = tmp_path_factory.mktemp("clearcut_synthetic_color")
    return make_synthetic_color_bg_image(directory / "synthetic_color.png")


@pytest.fixture(scope="session")
def cat_asset_path() -> Path:
    path = SAMPLES_INPUT / "cat.jpeg"
    if not path.is_file():
        pytest.skip("samples/input/cat.jpeg no disponible")
    return path


@pytest.fixture(scope="session")
def sticker_asset_path() -> Path:
    path = SAMPLES_INPUT / "sticker.png"
    if not path.is_file():
        pytest.skip("samples/input/sticker.png no disponible")
    return path
