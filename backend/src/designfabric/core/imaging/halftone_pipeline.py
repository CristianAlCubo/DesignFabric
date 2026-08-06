"""Pipeline de semitonos (halftone) para print-on-demand / serigrafía.

El core de este módulo —`_apply_levels`, `_auto_crop_black`, `_make_halftone_pattern`
y `make_halftone_single`— se extrae *verbatim* (sin cambios algorítmicos) del
HuggingFace Space `halftone-converter` (app Gradio), del cual solo se descarta la
capa de UI. Se mantiene la salida pixel-idéntica al original de forma deliberada:
cualquier refactor debe hacerse con tests de regresión que fijen la salida actual.

Atribución: algoritmo original del Space `halftone-converter` (Gradio + PIL + numpy).

Sobre `make_halftone_single`: genera un PNG RGBA transparente donde el patrón de
semitonos vive en el canal alpha y los colores originales se conservan en RGB. La
resolución y el DPI de salida se fijan en 4500×5400 @300 (igual que el Gradio, que
los hardcodeaba y no los exponía como controles) — ver `FULL_TARGET_PIXELS` /
`FULL_TARGET_DPI`.

`make_halftone_preview` es un wrapper delgado (no forma parte del core original)
que renderiza a resolución reducida escalando el DPI por el mismo factor, de modo
que `px_per_cycle = dpi / frequency` queda proporcional al tamaño de la imagen y el
punto conserva su tamaño *relativo* respecto del export full-res.
"""

from __future__ import annotations

import math
from typing import Literal

import numpy as np
from PIL import Image, ImageOps

HalftoneMethod = Literal["halftone", "diffusion"]
DotShape = Literal["round", "line"]

# Resolución/DPI de salida fijos, replicando el comportamiento hardcodeado del Gradio.
FULL_TARGET_PIXELS: tuple[int, int] = (4500, 5400)
FULL_TARGET_DPI: int = 300

# --- Helper Functions (verbatim del Space) -----------------------------------


def _apply_levels(gray_img, black_point=8, white_point=180, gamma=1.0):
    """Photoshop-style Levels adjustment."""
    bp, wp = float(black_point), float(white_point)
    rng = max(wp - bp, 1.0)

    def _map(v):
        v = float(v)
        if v <= bp:
            return 0
        if v >= wp:
            return 255
        norm = (v - bp) / rng
        if gamma != 1.0:
            norm = pow(norm, 1.0 / gamma)
        return int(norm * 255 + 0.5)

    return gray_img.point(_map)


def _auto_crop_black(img, threshold=20):
    """
    Crops away borders where all channels are below `threshold`.
    Works on RGB or RGBA images.
    """
    arr = np.array(img.convert("RGB"))
    mask = np.any(arr > threshold, axis=2)

    if not np.any(mask):
        return img

    y, x = np.where(mask)
    bbox = (x.min(), y.min(), x.max() + 1, y.max() + 1)
    return img.crop(bbox)


def _make_halftone_pattern(size, frequency_lpi, angle_deg, shape="round", dpi=300):
    """
    Creates a halftone threshold matrix rotated by `angle_deg`.
    """
    px_per_cycle = dpi / frequency_lpi
    w, h = size
    yy, xx = np.mgrid[0:h, 0:w]
    angle = math.radians(angle_deg)

    xr = xx * math.cos(angle) + yy * math.sin(angle)

    if shape == "line":
        pattern = 0.5 * (1 + np.sin(2 * math.pi * xr / px_per_cycle))
    else:  # round
        yr = -xx * math.sin(angle) + yy * math.cos(angle)
        pattern = 0.5 * (
            1
            + np.sin(2 * math.pi * xr / px_per_cycle)
            * np.sin(2 * math.pi * yr / px_per_cycle)
        )

    return (pattern * 255).astype(np.uint8)


# --- Main Function (verbatim del Space) --------------------------------------


def make_halftone_single(
    image,
    target_pixels=FULL_TARGET_PIXELS,
    target_dpi=FULL_TARGET_DPI,
    crop_black_background=True,
    crop_black_threshold=25,
    black_point=16,
    white_point=100,
    gamma=1.0,
    invert_for_dark_shirt=False,
    halftone_method="halftone",
    screen_frequency=35,
    screen_angle=23.5,
    dot_shape="round",
):
    """Generates a halftone version of a single image."""
    original = image.convert("RGBA")

    # 1) Remove black borders
    if crop_black_background:
        cropped = _auto_crop_black(original, threshold=crop_black_threshold)
    else:
        cropped = original

    # 2) Resize preserving aspect ratio
    resized = cropped.copy()
    resized.thumbnail(target_pixels, Image.LANCZOS)

    # 3) Grayscale + Levels
    gray = resized.convert("L")
    gray = _apply_levels(
        gray,
        black_point=black_point,
        white_point=white_point,
        gamma=gamma,
    )

    if invert_for_dark_shirt:
        gray = ImageOps.invert(gray)

    # 4) Generate halftone
    if halftone_method.lower() == "diffusion":
        halftoned = gray.convert("1", dither=Image.FLOYDSTEINBERG)
        alpha = halftoned.convert("L")
    else:
        pattern = _make_halftone_pattern(
            gray.size,
            screen_frequency,
            screen_angle,
            dot_shape,
            dpi=target_dpi,
        )
        arr_gray = np.array(gray, dtype=np.uint8)
        alpha_arr = np.where(arr_gray > pattern, 255, 0).astype(np.uint8)
        alpha = Image.fromarray(alpha_arr, mode="L")

    # 5) Apply alpha channel — keep original colors
    color = resized.convert("RGBA")
    color.putalpha(alpha)
    out_img = color

    # 6) Set DPI metadata
    out_img.info["dpi"] = (target_dpi, target_dpi)

    return out_img


# --- Preview wrapper (no forma parte del core original) ----------------------


def make_halftone_preview(
    image,
    *,
    preview_max_side: int = 1080,
    crop_black_background=True,
    crop_black_threshold=25,
    black_point=16,
    white_point=100,
    gamma=1.0,
    invert_for_dark_shirt=False,
    halftone_method="halftone",
    screen_frequency=35,
    screen_angle=23.5,
    dot_shape="round",
):
    """Render de previsualización a resolución reducida, representativo del export full-res.

    El punto del halftone depende de `px_per_cycle = dpi / frequency` en píxeles de
    salida. Para que el preview (mucho más chico) muestre el punto con el mismo tamaño
    *relativo* que el export, se escala tanto la caja de salida como el DPI por el mismo
    factor `r = preview_max_side / max(FULL_TARGET_PIXELS)`. Así `px_per_cycle` queda
    proporcional al tamaño de imagen y el patrón se ve como en el resultado final.

    Nota: el método `diffusion` (Floyd–Steinberg) no escala linealmente con la
    resolución, por lo que su preview es solo aproximado (se comunica en la UI).
    """
    full_long_side = max(FULL_TARGET_PIXELS)
    ratio = preview_max_side / full_long_side
    preview_pixels = (
        max(1, round(FULL_TARGET_PIXELS[0] * ratio)),
        max(1, round(FULL_TARGET_PIXELS[1] * ratio)),
    )
    preview_dpi = max(1.0, FULL_TARGET_DPI * ratio)

    return make_halftone_single(
        image,
        target_pixels=preview_pixels,
        target_dpi=preview_dpi,
        crop_black_background=crop_black_background,
        crop_black_threshold=crop_black_threshold,
        black_point=black_point,
        white_point=white_point,
        gamma=gamma,
        invert_for_dark_shirt=invert_for_dark_shirt,
        halftone_method=halftone_method,
        screen_frequency=screen_frequency,
        screen_angle=screen_angle,
        dot_shape=dot_shape,
    )


__all__ = [
    "FULL_TARGET_DPI",
    "FULL_TARGET_PIXELS",
    "DotShape",
    "HalftoneMethod",
    "make_halftone_preview",
    "make_halftone_single",
]
