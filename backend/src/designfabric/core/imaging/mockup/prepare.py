"""Preparación offline de recursos para plantillas de mockup."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import cv2
import numpy as np
from PIL import Image

from designfabric.core.config import get_settings
from designfabric.core.imaging.background_removal_strategies import RemovalModelPaths
from designfabric.core.imaging.mockup.template import (
    Corners,
    MockupTemplate,
    load_template,
)

_TEMPLATE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")


@dataclass(frozen=True, slots=True)
class PreparedTemplate:
    """Imágenes propuestas a partir de una foto para revisión humana."""

    base: Image.Image
    garment_mask: Image.Image
    shading: Image.Image
    displacement: Image.Image


def prepare_template(
    photo: Image.Image,
    mask: Image.Image | np.ndarray | None = None,
    *,
    model_paths: RemovalModelPaths | None = None,
) -> PreparedTemplate:
    """Propone máscara, sombreado y desplazamiento desde una foto RGB.

    La máscara resultante es una propuesta editable, no una segmentación
    definitiva. Una máscara recibida explícitamente siempre tiene prioridad.
    """
    base = photo.convert("RGB")
    rgb = np.asarray(base, dtype=np.uint8)
    height, width = rgb.shape[:2]
    if width < 1 or height < 1:
        raise ValueError("La foto debe tener dimensiones mayores que cero")

    if mask is None:
        garment_mask = _propose_mask(rgb, model_paths)
    else:
        garment_mask = _normalize_mask(mask, (width, height))
    if not np.any(garment_mask):
        raise ValueError("La máscara de la prenda está vacía")

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    shading, displacement = _derive_maps(gray, garment_mask)
    return PreparedTemplate(
        base=base.copy(),
        garment_mask=Image.fromarray(garment_mask, mode="L"),
        shading=Image.fromarray(shading, mode="L"),
        displacement=Image.fromarray(displacement, mode="L"),
    )


def save_template(
    directory: Path,
    photo: Image.Image,
    *,
    template_id: str,
    name: str,
    corners: Corners | Sequence[Sequence[float]],
    px_per_cm: float,
    mask: Image.Image | np.ndarray | None = None,
    model_paths: RemovalModelPaths | None = None,
    max_print_cm: tuple[float, float] = (30.0, 40.0),
    default_anchor: str = "top-center",
    displacement_strength_px: float = 6.0,
    shading_strength: float = 0.5,
    highlight_strength: float = 0.3,
    garment_colors: dict[str, str] | None = None,
    dark_garment_colors: tuple[str, ...] = (),
) -> MockupTemplate:
    """Escribe los PNG y el JSON v1; valida el resultado con `load_template`."""
    if not _TEMPLATE_ID.fullmatch(template_id):
        raise ValueError("id debe ser un identificador de carpeta simple")

    prepared = prepare_template(photo, mask, model_paths=model_paths)
    width, height = prepared.base.size
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    prepared.base.save(target / "base.png", format="PNG")
    prepared.garment_mask.save(target / "garment_mask.png", format="PNG")
    prepared.shading.save(target / "shading.png", format="PNG")
    prepared.displacement.save(target / "displacement.png", format="PNG")

    colors = garment_colors or {"blanco": "#FFFFFF", "negro": "#1A1A1A"}
    metadata = {
        "schema_version": 1,
        "id": template_id,
        "name": name,
        "base_size": [width, height],
        "print_area": {"corners": [[float(value) for value in point] for point in corners]},
        "px_per_cm": float(px_per_cm),
        "max_print_cm": [float(max_print_cm[0]), float(max_print_cm[1])],
        "default_anchor": default_anchor,
        "displacement_strength_px": float(displacement_strength_px),
        "shading_strength": float(shading_strength),
        "highlight_strength": float(highlight_strength),
        "garment_colors": colors,
        "dark_garment_colors": list(dark_garment_colors),
    }
    (target / "template.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return load_template(target)


def _propose_mask(rgb: np.ndarray, model_paths: RemovalModelPaths | None) -> np.ndarray:
    paths = model_paths
    if paths is None:
        settings = get_settings()
        paths = RemovalModelPaths(
            sam2_encoder_onnx=Path(settings.sam2_encoder_onnx) if settings.sam2_encoder_onnx else None,
            sam2_decoder_onnx=Path(settings.sam2_decoder_onnx) if settings.sam2_decoder_onnx else None,
        )

    if paths.sam2_encoder_onnx is not None and paths.sam2_decoder_onnx is not None:
        from designfabric.core.imaging.sam2_vitmatte.mask_selection import clean_mask, select_primary_mask
        from designfabric.core.imaging.sam2_vitmatte.sam2_session import Sam2OnnxSession

        image_bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        height, width = rgb.shape[:2]
        candidates = Sam2OnnxSession(paths.sam2_encoder_onnx, paths.sam2_decoder_onnx).predict_masks(
            image_bgr,
            point_xy=(width / 2.0, height / 2.0),
        )
        result = clean_mask(select_primary_mask(candidates))
        if not np.any(result):
            raise ValueError("SAM2 no propuso una máscara de prenda; proporciona una máscara manual")
        return result

    gray = cv2.cvtColor(rgb, cv2.COLOR_RGB2GRAY)
    height, width = gray.shape
    border_size = max(1, min(width, height) // 20)
    border = np.concatenate(
        (
            gray[:border_size, :].ravel(),
            gray[-border_size:, :].ravel(),
            gray[:, :border_size].ravel(),
            gray[:, -border_size:].ravel(),
        )
    )
    background_luminance = int(np.median(border))
    difference = cv2.absdiff(gray, np.full_like(gray, background_luminance))
    _, thresholded = cv2.threshold(
        difference,
        0,
        255,
        cv2.THRESH_BINARY | cv2.THRESH_OTSU,
    )
    result = _largest_component(thresholded)
    if not np.any(result):
        raise ValueError("No se pudo proponer una máscara; proporciona una máscara manual")
    return result


def _normalize_mask(mask: Image.Image | np.ndarray, size: tuple[int, int]) -> np.ndarray:
    if isinstance(mask, Image.Image):
        mask_array = np.asarray(mask.convert("L"), dtype=np.uint8)
    else:
        mask_array = np.asarray(mask)
        if mask_array.ndim != 2:
            raise ValueError("La máscara debe ser una imagen de un solo canal")
        if mask_array.dtype != np.uint8:
            mask_array = np.clip(mask_array, 0, 255).astype(np.uint8)
    if mask_array.shape != (size[1], size[0]):
        raise ValueError(f"La máscara debe medir {size[0]}×{size[1]} píxeles")
    return np.where(mask_array > 0, 255, 0).astype(np.uint8)


def _largest_component(mask: np.ndarray) -> np.ndarray:
    binary = np.where(mask > 0, 1, 0).astype(np.uint8)
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if count <= 1:
        return np.zeros_like(mask)
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    return np.where(labels == largest_label, 255, 0).astype(np.uint8)


def _derive_maps(gray: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    luminance = gray.astype(np.float32)
    active = mask > 0
    median = float(np.median(luminance[active]))
    if not math.isfinite(median) or median <= 0:
        median = 0.0

    height, width = gray.shape
    side = min(width, height)
    shading_sigma = max(0.8, side * 0.002)
    shading = luminance * (128.0 / median) if median > 0 else np.full_like(luminance, 128.0)
    shading[~active] = 128.0
    shading = _gaussian_blur(shading, shading_sigma)
    shading_median = float(np.median(shading[active]))
    if shading_median > 0:
        shading[active] *= 128.0 / shading_median
    shading[~active] = 128.0

    displacement_sigma = max(1.0, side * 0.01)
    displacement = _gaussian_blur(luminance, displacement_sigma)
    displacement[active] += 128.0 - float(np.mean(displacement[active]))
    displacement[~active] = 128.0
    for _ in range(2):
        displacement[active] += 128.0 - float(np.mean(displacement[active]))
    return _to_uint8(shading), _to_uint8(displacement)


def _gaussian_blur(image: np.ndarray, sigma: float) -> np.ndarray:
    radius = max(1, int(math.ceil(sigma * 3.0)))
    kernel_size = radius * 2 + 1
    return cv2.GaussianBlur(
        image.astype(np.float32),
        (kernel_size, kernel_size),
        sigmaX=sigma,
        sigmaY=sigma,
        borderType=cv2.BORDER_REFLECT,
    )


def _to_uint8(image: np.ndarray) -> np.ndarray:
    return np.rint(image).clip(0, 255).astype(np.uint8)
