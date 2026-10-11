"""Modos «rápido» y «avanzado» de semitonos, como capa sobre el core verbatim.

`halftone_pipeline` conserva el algoritmo del Space sin cambios. Este módulo lo
envuelve para resolver tres problemas del uso real en DTF:

1. **Fondo**: el core ignora el alpha de entrada (un PNG con fondo transparente
   salía con el fondo opaco) y solo sabe recortar fondo negro. Aquí se detecta el
   fondo (transparente / negro / blanco / ninguno), se construye una máscara del
   sujeto, se recorta a ella y se intersecta con el alpha de la trama: el fondo
   nunca recibe tinta, sea cual sea la prenda.
2. **Prenda**: el core pone tinta donde la imagen es *clara* salvo que se invierta.
   Eso es lo correcto para prenda oscura (lo oscuro deja ver la tela); en prenda
   clara hay que invertir. El flag original `invert_for_dark_shirt` está nombrado
   al revés, así que aquí se expone `garment` y se mapea explícitamente.
3. **Punto mínimo**: el core genera puntos arbitrariamente chicos en los tonos
   extremos, que en DTF no adhieren. Aquí la matriz de umbrales se limita a
   `[min_dot_tone, 255 - min_dot_tone]`: los tonos más claros que eso quedan sin
   tinta y los más oscuros, sólidos, sin puntos ni huecos intermedios diminutos.
   Ojo: subir el punto negro *no* sirve para esto, porque Levels estira el rango y
   los tonos justo por encima siguen dando puntos diminutos. Con `min_dot_tone=0`
   el render es pixel-idéntico a `make_halftone_single` (fijado por test).
4. **Modo rápido**: niveles por histograma del sujeto, trama redonda fija y
   `min_dot_tone` calibrado midiendo el patrón real contra `MIN_DOT_MM`. Los
   parámetros resueltos se devuelven para que el modo avanzado arranque desde ellos.

El render reimplementa los pasos de `make_halftone_single` usando sus helpers
verbatim (`_apply_levels`, `_make_halftone_pattern`) porque el límite del patrón
no se puede inyectar en la función original sin modificarla.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, replace
from typing import Literal

import cv2
import numpy as np
from PIL import Image

from functools import lru_cache

from PIL import ImageOps

from designfabric.core.imaging.halftone_pipeline import (
    FULL_TARGET_DPI,
    FULL_TARGET_PIXELS,
    DotShape,
    HalftoneMethod,
    _apply_levels,
    _make_halftone_pattern,
)

Garment = Literal["light", "dark"]
BackgroundMode = Literal["auto", "transparent", "black", "white", "none"]
DetectedBackground = Literal["transparent", "black", "white", "none"]

# Parámetros de trama fijos del modo rápido. El patrón `sin·sin` del core pone dos
# puntos por ciclo, así que su LPI nominal se comporta como ~√2 veces más fino que
# una trama convencional: 25 aquí ≈ 35 LPI convencionales, típico de DTF.
QUICK_SCREEN_FREQUENCY = 25
QUICK_SCREEN_ANGLE = 22.5

# Diámetro mínimo de punto/hueco que adhiere bien en DTF.
MIN_DOT_MM = 0.25

# Resolución de análisis (niveles y validación); se renderiza a DPI completo para
# que el tamaño del punto en píxeles coincida con el export.
ANALYSIS_MAX_SIDE = 1024

# Validador: fracción máxima tolerada del área de la trama que vive en componentes
# por debajo del mínimo (siempre hay algo de fragmento en las uniones del 50 %).
MAX_SMALL_DOT_RATIO = 0.1
_MAX_MIN_DOT_TONE = 100

# Mínimo de rango tonal para tratar el sujeto como «con degradados».
_FLAT_RANGE = 16
# Fracción de píxeles en tonos medios por debajo de la cual el semitono no aporta.
_FLAT_MIDTONE_RATIO = 0.03
# Lado mayor (px @300) por debajo del cual se avisa de impresión pequeña (~20 cm).
_SMALL_PRINT_PX = 2400


@dataclass(frozen=True)
class HalftoneSettings:
    """Parámetros completos de un render (los del core + prenda y fondo)."""

    garment: Garment = "dark"
    background: BackgroundMode = "auto"
    background_threshold: int = 25
    black_point: int = 16
    white_point: int = 100
    gamma: float = 1.0
    halftone_method: HalftoneMethod = "halftone"
    screen_frequency: int = 35
    screen_angle: float = 23.5
    dot_shape: DotShape = "round"
    min_dot_tone: int = 0


@dataclass(frozen=True)
class HalftoneAnalysis:
    """Parámetros resueltos (fondo ya detectado) más diagnóstico de imprimibilidad."""

    settings: HalftoneSettings
    background: DetectedBackground
    small_dot_ratio: float
    output_size: tuple[int, int]
    warnings: tuple[str, ...]


# --- Fondo y máscara del sujeto ----------------------------------------------


def _border(arr: np.ndarray) -> np.ndarray:
    return np.concatenate([arr[0], arr[-1], arr[:, 0], arr[:, -1]])


def detect_background(image: Image.Image, threshold: int = 25) -> DetectedBackground:
    """Clasifica el fondo: transparencia real, o un borde mayoritariamente negro/blanco."""
    rgba = image.convert("RGBA")
    alpha = np.asarray(rgba.getchannel("A"))
    if (alpha < 128).mean() > 0.02:
        return "transparent"

    lum = _border(np.asarray(rgba.convert("L")))
    if (lum <= threshold).mean() >= 0.6:
        return "black"
    if (lum >= 255 - threshold).mean() >= 0.6:
        return "white"
    return "none"


def subject_mask(
    image: Image.Image, background: DetectedBackground, threshold: int = 25
) -> np.ndarray:
    """Máscara booleana del sujeto (True = puede llevar tinta).

    Para fondo negro/blanco solo se descartan las regiones de ese color *conectadas
    al borde*: los negros/blancos interiores del diseño se conservan.
    """
    rgba = image.convert("RGBA")
    if background == "transparent":
        mask = np.asarray(rgba.getchannel("A")) >= 128
    elif background in ("black", "white"):
        lum = np.asarray(rgba.convert("L"))
        candidate = lum <= threshold if background == "black" else lum >= 255 - threshold
        _, labels = cv2.connectedComponents(candidate.astype(np.uint8), connectivity=4)
        border_labels = np.unique(_border(labels)[_border(candidate)])
        bg = np.isin(labels, border_labels) & candidate
        # Se come 1 px del borde del sujeto: el antialias contra el fondo deja un
        # halo casi negro/blanco que, con la prenda «contraria», imprimiría un aro.
        bg = cv2.dilate(bg.astype(np.uint8), np.ones((3, 3), np.uint8)) > 0
        mask = ~bg
    else:
        mask = np.ones((rgba.height, rgba.width), dtype=bool)

    if not mask.any():
        return np.ones_like(mask)
    return mask


def _crop_to_mask(image: Image.Image, mask: np.ndarray) -> tuple[Image.Image, np.ndarray]:
    ys, xs = np.where(mask)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    return image.crop((x0, y0, x1, y1)), mask[y0:y1, x0:x1]


def _thumbnail_size(size: tuple[int, int], box: tuple[int, int]) -> tuple[int, int]:
    """Tamaño que deja `Image.thumbnail` (solo reduce, conserva proporción)."""
    w, h = size
    scale = min(1.0, box[0] / w, box[1] / h)
    return max(1, round(w * scale)), max(1, round(h * scale))


# --- Render -------------------------------------------------------------------


def _halftone_core(
    image: Image.Image,
    settings: HalftoneSettings,
    target_pixels: tuple[int, int],
    target_dpi: float,
) -> Image.Image:
    """Pasos 2–6 de `make_halftone_single` (sin recorte negro) + límite del patrón."""
    resized = image.copy()
    resized.thumbnail(target_pixels, Image.Resampling.LANCZOS)

    gray = _apply_levels(
        resized.convert("L"),
        black_point=settings.black_point,
        white_point=settings.white_point,
        gamma=settings.gamma,
    )
    if settings.garment == "light":
        gray = ImageOps.invert(gray)

    if settings.halftone_method == "diffusion":
        alpha = gray.convert("1", dither=Image.Dither.FLOYDSTEINBERG).convert("L")
    else:
        pattern = _make_halftone_pattern(
            gray.size,
            settings.screen_frequency,
            settings.screen_angle,
            settings.dot_shape,
            dpi=target_dpi,
        )
        if settings.min_dot_tone > 0:
            pattern = np.clip(pattern, settings.min_dot_tone, 255 - settings.min_dot_tone)
        arr_gray = np.array(gray, dtype=np.uint8)
        alpha = Image.fromarray(np.where(arr_gray > pattern, 255, 0).astype(np.uint8), mode="L")

    out = resized.convert("RGBA")
    out.putalpha(alpha)
    return out


def _resolve_background(image: Image.Image, settings: HalftoneSettings) -> DetectedBackground:
    if settings.background == "auto":
        return detect_background(image, settings.background_threshold)
    return settings.background


def render_halftone(
    image: Image.Image,
    settings: HalftoneSettings,
    *,
    target_pixels: tuple[int, int] = FULL_TARGET_PIXELS,
    target_dpi: float = FULL_TARGET_DPI,
) -> Image.Image:
    """Render a tamaño de salida con manejo de fondo, prenda y punto mínimo."""
    rgba = image.convert("RGBA")
    background = _resolve_background(rgba, settings)
    cropped, mask = _crop_to_mask(rgba, subject_mask(rgba, background, settings.background_threshold))

    out = _halftone_core(cropped, settings, target_pixels, target_dpi)

    mask_img = Image.fromarray(mask.astype(np.uint8) * 255, mode="L").resize(
        out.size, Image.Resampling.BILINEAR
    )
    alpha = np.asarray(out.getchannel("A"))
    alpha = np.where(np.asarray(mask_img) >= 128, alpha, 0).astype(np.uint8)
    out.putalpha(Image.fromarray(alpha, mode="L"))
    out.info["dpi"] = (target_dpi, target_dpi)
    return out


def render_halftone_preview(
    image: Image.Image, settings: HalftoneSettings, *, preview_max_side: int = 1080
) -> Image.Image:
    """Preview a baja resolución con el punto en el mismo tamaño *relativo* que el export.

    A diferencia de `make_halftone_preview`, el factor se calcula sobre el tamaño
    real de salida (el core nunca agranda): con una entrada de 1000 px el export
    sale a 1000 px, y escalar el DPI según la caja de 4500×5400 encogería el punto.
    """
    full_size = _full_output_size(image, settings)
    ratio = min(1.0, preview_max_side / max(full_size))
    return render_halftone(
        image,
        settings,
        target_pixels=_thumbnail_size(full_size, (preview_max_side, preview_max_side)),
        target_dpi=max(1.0, FULL_TARGET_DPI * ratio),
    )


def _full_output_size(image: Image.Image, settings: HalftoneSettings) -> tuple[int, int]:
    rgba = image.convert("RGBA")
    background = _resolve_background(rgba, settings)
    cropped, _ = _crop_to_mask(rgba, subject_mask(rgba, background, settings.background_threshold))
    return _thumbnail_size(cropped.size, FULL_TARGET_PIXELS)


# --- Análisis / validación ----------------------------------------------------


def _min_dot_area_px(dpi: float) -> float:
    diameter = MIN_DOT_MM / 25.4 * dpi
    return math.pi / 4 * diameter * diameter


def small_dot_ratio(halftone: Image.Image, dpi: float = FULL_TARGET_DPI) -> float:
    """Fracción del área tramada (puntos de tinta + huecos) que pertenece a componentes
    más chicos que el mínimo imprimible.

    Se pondera por área y no por cantidad: los fragmentos de 1–2 px que deja la
    rasterización en las uniones del 50 % son numerosos pero casi no llevan tinta.
    Las zonas sólidas y el fondo son componentes grandes y no cuentan como pequeños.
    """
    opaque = (np.asarray(halftone.getchannel("A")) > 0).astype(np.uint8)
    min_area = _min_dot_area_px(dpi)
    small = 0
    tramado = 0
    for layer in (opaque, 1 - opaque):
        _, _, stats, _ = cv2.connectedComponentsWithStats(layer, connectivity=8)
        areas = stats[1:, cv2.CC_STAT_AREA]
        # Los componentes muy grandes (zonas sólidas, fondo, trama unida) no son puntos.
        dots = areas[areas < min_area * 40]
        tramado += int(dots.sum())
        small += int(dots[dots < min_area].sum())
    return small / tramado if tramado else 0.0


def _subject_gray(image: Image.Image, background: DetectedBackground, threshold: int) -> np.ndarray:
    rgba = image.convert("RGBA")
    mask = subject_mask(rgba, background, threshold)
    return np.asarray(rgba.convert("L"))[mask]


def _analysis_image(image: Image.Image) -> Image.Image:
    small = image.convert("RGBA")
    small.thumbnail((ANALYSIS_MAX_SIDE, ANALYSIS_MAX_SIDE), Image.Resampling.LANCZOS)
    return small


def _warnings(
    settings: HalftoneSettings,
    background: DetectedBackground,
    gray: np.ndarray,
    output_size: tuple[int, int],
    dot_ratio: float,
) -> list[str]:
    warnings: list[str] = []
    long_side = max(output_size)
    if long_side < _SMALL_PRINT_PX:
        cm = long_side / FULL_TARGET_DPI * 2.54
        warnings.append(
            f"La imagen imprimirá a solo {cm:.1f} cm de lado mayor a 300 DPI; "
            "considera escalarla antes."
        )
    if background == "none":
        warnings.append("No se detectó un fondo uniforme: se trama la imagen completa.")

    if gray.size:
        lo, hi = settings.black_point, settings.white_point
        midtones = ((gray > lo) & (gray < hi)).mean() if hi > lo else 0.0
        if midtones < _FLAT_MIDTONE_RATIO:
            warnings.append(
                "El diseño casi no tiene tonos intermedios: el semitono apenas cambiará el "
                "resultado."
            )

    if settings.halftone_method == "diffusion":
        warnings.append(
            "«Difusión» genera puntos de 1 px (~0,08 mm a 300 DPI) que pueden no adherir "
            "bien en DTF."
        )
    elif dot_ratio > MAX_SMALL_DOT_RATIO:
        warnings.append(
            f"El {dot_ratio:.0%} de la trama son puntos menores de {MIN_DOT_MM} mm que "
            "podrían no adherir: sube el punto mínimo o reduce la frecuencia."
        )
    return warnings


def _measure(image: Image.Image, settings: HalftoneSettings) -> float:
    # DPI completo sobre la imagen de análisis: el punto mide en px lo mismo que en el
    # export, que es lo que importa para imprimibilidad.
    rendered = render_halftone(image, settings, target_pixels=image.size)
    return small_dot_ratio(rendered, FULL_TARGET_DPI)


def analyze_halftone(image: Image.Image, settings: HalftoneSettings) -> HalftoneAnalysis:
    """Diagnóstico de unos parámetros dados (modo avanzado), sin modificarlos."""
    analysis_img = _analysis_image(image)
    background = _resolve_background(image, settings)
    resolved = replace(settings, background=background)
    dot_ratio = 0.0 if settings.halftone_method == "diffusion" else _measure(analysis_img, resolved)
    gray = _subject_gray(analysis_img, background, settings.background_threshold)
    output_size = _full_output_size(image, resolved)
    return HalftoneAnalysis(
        settings=resolved,
        background=background,
        small_dot_ratio=dot_ratio,
        output_size=output_size,
        warnings=tuple(_warnings(resolved, background, gray, output_size, dot_ratio)),
    )


def _quick_levels(gray: np.ndarray, garment: Garment) -> tuple[int, int]:
    """Niveles por percentiles del sujeto: usa todo su rango tonal sin quemarlo."""
    lo, hi = (float(v) for v in np.percentile(gray, [2, 98])) if gray.size else (0.0, 255.0)
    if hi - lo < _FLAT_RANGE:
        # Sujeto de un solo tono: que imprima sólido en vez de una trama uniforme.
        tone = int(round((lo + hi) / 2))
        return (0, max(1, tone)) if garment == "dark" else (min(254, tone), 255)
    return int(round(lo)), max(int(round(hi)), int(round(lo)) + 1)


@lru_cache(maxsize=64)
def min_dot_tone_for(
    frequency: int, angle: float, shape: DotShape = "round", min_dot_mm: float = MIN_DOT_MM
) -> int:
    """Menor tono (0–255) cuyo punto típico alcanza `min_dot_mm` a DPI completo.

    Se mide sobre el patrón real del core: su geometría `sin·sin` no se presta a una
    fórmula cerrada. Para «línea» el criterio es el grosor de la línea.
    """
    cycle_px = FULL_TARGET_DPI / frequency
    if shape == "line":
        min_px = min_dot_mm / 25.4 * FULL_TARGET_DPI
        return min(_MAX_MIN_DOT_TONE, math.ceil(min_px / cycle_px * 255))

    side = int(cycle_px * 10) + 1
    pattern = _make_halftone_pattern((side, side), frequency, angle, "round", FULL_TARGET_DPI)
    min_area = _min_dot_area_px(FULL_TARGET_DPI)
    for tone in range(1, _MAX_MIN_DOT_TONE + 1):
        ink = (tone > pattern).astype(np.uint8)
        _, _, stats, _ = cv2.connectedComponentsWithStats(ink, connectivity=8)
        areas = stats[1:, cv2.CC_STAT_AREA]
        if areas.size and np.median(areas) >= min_area:
            return tone
    return _MAX_MIN_DOT_TONE


def resolve_quick_halftone(
    image: Image.Image,
    *,
    garment: Garment,
    background: BackgroundMode = "auto",
    background_threshold: int = 25,
) -> HalftoneAnalysis:
    """Elige automáticamente unos parámetros que se vean bien e impriman en la mayoría
    de los casos: trama redonda fija, niveles por histograma y punto mínimo
    calibrado contra el tamaño mínimo de punto."""
    analysis_img = _analysis_image(image)
    base = HalftoneSettings(
        garment=garment,
        background=background,
        background_threshold=background_threshold,
        gamma=1.0,
        halftone_method="halftone",
        screen_frequency=QUICK_SCREEN_FREQUENCY,
        screen_angle=QUICK_SCREEN_ANGLE,
        dot_shape="round",
    )
    detected = _resolve_background(image, base)
    base = replace(base, background=detected)
    gray = _subject_gray(analysis_img, detected, background_threshold)

    black, white = _quick_levels(gray, garment)
    settings = replace(
        base,
        black_point=black,
        white_point=white,
        min_dot_tone=min_dot_tone_for(QUICK_SCREEN_FREQUENCY, QUICK_SCREEN_ANGLE),
    )
    dot_ratio = _measure(analysis_img, settings)

    output_size = _full_output_size(image, settings)
    return HalftoneAnalysis(
        settings=settings,
        background=detected,
        small_dot_ratio=dot_ratio,
        output_size=output_size,
        warnings=tuple(_warnings(settings, detected, gray, output_size, dot_ratio)),
    )


__all__ = [
    "BackgroundMode",
    "DetectedBackground",
    "Garment",
    "HalftoneAnalysis",
    "HalftoneSettings",
    "analyze_halftone",
    "detect_background",
    "min_dot_tone_for",
    "render_halftone",
    "render_halftone_preview",
    "resolve_quick_halftone",
    "small_dot_ratio",
    "subject_mask",
]
