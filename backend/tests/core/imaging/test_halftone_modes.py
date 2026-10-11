"""Tests de los modos rápido/avanzado de semitonos (`halftone_modes`).

Cobertura: equivalencia con el core verbatim cuando no se usan las extensiones,
manejo de fondo (transparente / negro / blanco), mapeo de prenda, punto mínimo,
resolución automática del modo rápido y avisos.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from designfabric.core.imaging.halftone_modes import (
    MAX_SMALL_DOT_RATIO,
    HalftoneSettings,
    analyze_halftone,
    detect_background,
    render_halftone,
    render_halftone_preview,
    resolve_quick_halftone,
    small_dot_ratio,
    subject_mask,
)
from designfabric.core.imaging.halftone_pipeline import make_halftone_single

BOX = (160, 160)


def _gradient_rgb(size: int = 160) -> Image.Image:
    g = np.tile(np.linspace(0, 255, size).astype(np.uint8), (size, 1))
    return Image.fromarray(np.dstack([g, g, g]), mode="RGB")


def _disc_on(background: tuple[int, int, int, int], size: int = 160) -> Image.Image:
    """Disco con degradado horizontal sobre un fondo dado (RGBA)."""
    arr = np.zeros((size, size, 4), np.uint8)
    arr[...] = background
    yy, xx = np.mgrid[0:size, 0:size]
    inside = np.hypot(xx - size / 2, yy - size / 2) < size * 0.35
    tone = (40 + xx * 180 // size).astype(np.uint8)
    arr[inside, 0] = tone[inside]
    arr[inside, 1] = tone[inside]
    arr[inside, 2] = tone[inside]
    arr[inside, 3] = 255
    return Image.fromarray(arr, mode="RGBA")


def _alpha(img: Image.Image) -> np.ndarray:
    return np.asarray(img.getchannel("A"))


# --- Equivalencia con el core -------------------------------------------------


@pytest.mark.parametrize(("garment", "invert"), [("dark", False), ("light", True)])
def test_matches_core_without_extensions(garment, invert) -> None:
    """Sin fondo, sin punto mínimo: pixel-idéntico al core con la inversión mapeada."""
    img = _gradient_rgb()
    params = {"black_point": 16, "white_point": 200, "screen_frequency": 35, "screen_angle": 23.5}
    ours = render_halftone(
        img,
        HalftoneSettings(garment=garment, background="none", **params),
        target_pixels=BOX,
    )
    core = make_halftone_single(
        img,
        target_pixels=BOX,
        crop_black_background=False,
        invert_for_dark_shirt=invert,
        **params,
    )
    assert np.array_equal(np.asarray(ours), np.asarray(core))


def test_garment_maps_ink_to_the_right_tones() -> None:
    """Prenda oscura: tinta en lo claro. Prenda clara: tinta en lo oscuro."""
    img = _gradient_rgb()
    for garment, ink_side, bare_side in (("dark", np.s_[:, -20:], np.s_[:, :20]),
                                         ("light", np.s_[:, :20], np.s_[:, -20:])):
        out = render_halftone(
            img,
            HalftoneSettings(garment=garment, background="none", black_point=0, white_point=255),
            target_pixels=BOX,
        )
        alpha = _alpha(out) > 0
        assert alpha[ink_side].mean() > 0.9, garment
        assert alpha[bare_side].mean() < 0.1, garment


# --- Fondo ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("background", "expected"),
    [
        ((255, 255, 255, 0), "transparent"),
        ((0, 0, 0, 255), "black"),
        ((255, 255, 255, 255), "white"),
    ],
)
def test_detect_background(background, expected) -> None:
    assert detect_background(_disc_on(background)) == expected


def test_detect_background_none_for_full_bleed_image() -> None:
    assert detect_background(_gradient_rgb()) == "none"


@pytest.mark.parametrize(
    "background", [(255, 255, 255, 0), (0, 0, 0, 0), (0, 0, 0, 255), (255, 255, 255, 255)]
)
@pytest.mark.parametrize("garment", ["dark", "light"])
def test_background_never_gets_ink(background, garment) -> None:
    """Regresión: el core ignoraba el alpha y un fondo transparente con RGB claro salía
    opaco; con fondo negro/blanco la prenda «contraria» lo llenaba de tinta."""
    img = _disc_on(background)
    out = render_halftone(
        img,
        HalftoneSettings(garment=garment, black_point=0, white_point=255),
        target_pixels=BOX,
    )
    alpha = _alpha(out)
    # Las esquinas quedan fuera del disco (recortado al sujeto): siempre sin tinta.
    for corner in (alpha[:8, :8], alpha[:8, -8:], alpha[-8:, :8], alpha[-8:, -8:]):
        assert corner.max() == 0
    assert alpha.max() == 255, "el sujeto sí recibe tinta"


def test_core_alone_fills_transparent_background() -> None:
    """Documenta el comportamiento del core que `halftone_modes` corrige."""
    out = make_halftone_single(_disc_on((255, 255, 255, 0)), target_pixels=BOX)
    assert _alpha(out)[:8, :8].min() == 255


def test_black_background_keeps_interior_blacks() -> None:
    """Solo se quita el negro conectado al borde; un negro dentro del diseño se conserva."""
    arr = np.zeros((100, 100, 3), np.uint8)
    arr[20:80, 20:80] = 255
    arr[40:60, 40:60] = 0  # «ojo» negro interior
    mask = subject_mask(Image.fromarray(arr), "black")
    assert not mask[0, 0]
    assert mask[50, 50]


def test_output_is_cropped_to_subject() -> None:
    img = _disc_on((255, 255, 255, 0))
    out = render_halftone(img, HalftoneSettings(), target_pixels=BOX)
    assert out.width < img.width and out.height < img.height


# --- Punto mínimo -------------------------------------------------------------


def test_min_dot_tone_removes_unprintable_dots() -> None:
    img = Image.fromarray(np.tile(np.linspace(0, 255, 512).astype(np.uint8), (512, 1)))
    base = HalftoneSettings(background="none", black_point=0, white_point=255)
    raw = render_halftone(img, base, target_pixels=img.size)
    clamped = render_halftone(
        img, HalftoneSettings(**{**base.__dict__, "min_dot_tone": 60}), target_pixels=img.size
    )
    assert small_dot_ratio(raw) > MAX_SMALL_DOT_RATIO
    assert small_dot_ratio(clamped) < small_dot_ratio(raw) / 2


# --- Modo rápido --------------------------------------------------------------


def test_quick_mode_produces_printable_dots_and_resolves_background() -> None:
    analysis = resolve_quick_halftone(_disc_on((0, 0, 0, 255), size=400), garment="dark")
    assert analysis.background == "black"
    assert analysis.settings.background == "black"
    assert analysis.settings.halftone_method == "halftone"
    assert analysis.settings.min_dot_tone > 0
    assert analysis.small_dot_ratio <= MAX_SMALL_DOT_RATIO


def test_quick_mode_levels_follow_subject_histogram() -> None:
    """El disco va de tono 40 a 220: los niveles deben ajustarse a ese rango, no al fijo
    16/100 del Space."""
    analysis = resolve_quick_halftone(_disc_on((255, 255, 255, 0), size=400), garment="dark")
    assert 40 <= analysis.settings.black_point < 90
    assert 170 < analysis.settings.white_point <= 220


@pytest.mark.parametrize("garment", ["dark", "light"])
def test_quick_mode_flat_design_prints_solid(garment) -> None:
    arr = np.zeros((200, 200, 4), np.uint8)
    arr[50:150, 50:150] = (130, 60, 200, 255)
    img = Image.fromarray(arr, mode="RGBA")
    analysis = resolve_quick_halftone(img, garment=garment)
    out = render_halftone(img, analysis.settings, target_pixels=BOX)
    assert (_alpha(out) == 255).all()
    assert any("tonos intermedios" in w for w in analysis.warnings)


def test_quick_mode_warns_on_small_print() -> None:
    analysis = resolve_quick_halftone(_disc_on((0, 0, 0, 255)), garment="dark")
    assert any("cm de lado mayor" in w for w in analysis.warnings)


def test_advanced_warns_on_diffusion_and_small_dots() -> None:
    img = _gradient_rgb(512)
    diffusion = analyze_halftone(img, HalftoneSettings(halftone_method="diffusion"))
    assert any("Difusión" in w for w in diffusion.warnings)

    # Valores del Space: 35 LPI sin punto mínimo dan trama no imprimible.
    raw = analyze_halftone(
        img, HalftoneSettings(background="none", black_point=0, white_point=255)
    )
    assert raw.small_dot_ratio > MAX_SMALL_DOT_RATIO
    assert any("podrían no adherir" in w for w in raw.warnings)


# --- Preview ------------------------------------------------------------------


def test_preview_of_small_image_matches_export() -> None:
    """Si el export cabe en el preview, se renderiza al mismo DPI: idénticos. El preview
    del core escalaba el DPI por la caja 4500×5400 y encogía el punto."""
    img = _disc_on((0, 0, 0, 255), size=300)
    settings = HalftoneSettings(background="black")
    preview = render_halftone_preview(img, settings, preview_max_side=1080)
    full = render_halftone(img, settings)
    assert np.array_equal(np.asarray(preview), np.asarray(full))
