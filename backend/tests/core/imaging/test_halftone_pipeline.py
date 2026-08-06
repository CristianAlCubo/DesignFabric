"""Tests del pipeline de semitonos (halftone).

Cobertura: propiedades de la salida (PNG RGBA, alpha binario para el método
`halftone`, DPI), efecto de crop/levels/invert/forma, y un test de regresión que
fija la salida sobre una imagen de referencia (hash de píxeles) para detectar
cualquier deriva algorítmica respecto del core extraído del Space.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pytest
from PIL import Image

from designfabric.core.imaging.halftone_pipeline import (
    FULL_TARGET_DPI,
    make_halftone_preview,
    make_halftone_single,
)

# Caja de salida chica para tests rápidos (el algoritmo es idéntico a cualquier tamaño).
SMALL_BOX = (120, 120)


def _gradient(size: tuple[int, int] = (128, 128)) -> Image.Image:
    """Gradiente RGB determinista, con variación en ambos ejes."""
    w, h = size
    xx, yy = np.meshgrid(np.arange(w), np.arange(h))
    r = (xx * 255 // max(w - 1, 1)).astype(np.uint8)
    g = (yy * 255 // max(h - 1, 1)).astype(np.uint8)
    b = ((xx + yy) * 255 // max(w + h - 2, 1)).astype(np.uint8)
    return Image.fromarray(np.dstack([r, g, b]), mode="RGB")


def _framed(inner_color=(200, 180, 60), border=16, size=(128, 128)) -> Image.Image:
    """Imagen con un borde negro alrededor de un rectángulo de color (para probar crop)."""
    img = Image.new("RGB", size, (0, 0, 0))
    w, h = size
    inner = Image.new("RGB", (w - 2 * border, h - 2 * border), inner_color)
    img.paste(inner, (border, border))
    return img


def test_output_is_rgba_png_with_dpi() -> None:
    out = make_halftone_single(_gradient(), target_pixels=SMALL_BOX)
    assert out.mode == "RGBA"
    assert out.info.get("dpi") == (FULL_TARGET_DPI, FULL_TARGET_DPI)


def test_halftone_method_produces_binary_alpha() -> None:
    out = make_halftone_single(
        _gradient(), target_pixels=SMALL_BOX, halftone_method="halftone"
    )
    alpha = np.array(out.split()[-1])
    assert set(np.unique(alpha)).issubset({0, 255}), "el screen de puntos da alpha binario"
    # Un gradiente debe producir zonas transparentes y zonas opacas.
    assert alpha.min() == 0
    assert alpha.max() == 255


def test_diffusion_method_produces_binary_alpha() -> None:
    out = make_halftone_single(
        _gradient(), target_pixels=SMALL_BOX, halftone_method="diffusion"
    )
    alpha = np.array(out.split()[-1])
    assert set(np.unique(alpha)).issubset({0, 255})


def test_crop_black_reduces_dimensions() -> None:
    framed = _framed()
    cropped = make_halftone_single(
        framed, target_pixels=SMALL_BOX, crop_black_background=True, crop_black_threshold=25
    )
    not_cropped = make_halftone_single(
        framed, target_pixels=SMALL_BOX, crop_black_background=False
    )
    # Con crop, el borde negro se recorta antes del thumbnail → distinta relación de aspecto/área útil.
    assert cropped.size != not_cropped.size or np.array(cropped).sum() != np.array(not_cropped).sum()


def test_invert_flips_alpha_coverage() -> None:
    base = make_halftone_single(
        _gradient(), target_pixels=SMALL_BOX, invert_for_dark_shirt=False
    )
    inverted = make_halftone_single(
        _gradient(), target_pixels=SMALL_BOX, invert_for_dark_shirt=True
    )
    cov_base = int(np.array(base.split()[-1]).astype(bool).sum())
    cov_inv = int(np.array(inverted.split()[-1]).astype(bool).sum())
    assert cov_base != cov_inv, "invertir debe cambiar la cobertura opaca"


def test_line_shape_differs_from_round() -> None:
    round_out = make_halftone_single(
        _gradient(), target_pixels=SMALL_BOX, dot_shape="round", screen_frequency=20
    )
    line_out = make_halftone_single(
        _gradient(), target_pixels=SMALL_BOX, dot_shape="line", screen_frequency=20
    )
    assert np.array(round_out).tobytes() != np.array(line_out).tobytes()


def test_preview_is_smaller_than_full() -> None:
    src = _gradient((256, 256))
    preview = make_halftone_preview(src, preview_max_side=120)
    full = make_halftone_single(src)  # caja 4500×5400
    assert max(preview.size) <= 120
    assert max(preview.size) < max(full.size)


@pytest.mark.parametrize("method", ["halftone", "diffusion"])
def test_regression_pixel_hash_is_stable(method: str) -> None:
    """Fija la salida sobre una imagen de referencia: si el algoritmo del core cambia,
    este hash cambia y el test falla (detección de deriva respecto del Space)."""
    src = _gradient((128, 128))
    out = make_halftone_single(
        src,
        target_pixels=SMALL_BOX,
        crop_black_background=False,
        black_point=16,
        white_point=100,
        gamma=1.0,
        halftone_method=method,
        screen_frequency=35,
        screen_angle=23.5,
        dot_shape="round",
    )
    digest = hashlib.sha256(np.array(out).tobytes()).hexdigest()
    expected = {
        "halftone": "9d9f575abaa9e3ec6b397e695b784c5665a3a8bf6592625092afc3adf287e14d",
        "diffusion": "3014f52a0c0b33159251630637f7433f087c23145f619b5a6c75c6a6f81d5ae1",
    }
    # El hash esperado se fija tras la primera corrida verde (ver nota del test).
    assert digest == expected[method], (
        f"hash de regresión '{method}' cambió a {digest!r}; "
        "actualizar SOLO si el cambio de salida es intencional."
    )
