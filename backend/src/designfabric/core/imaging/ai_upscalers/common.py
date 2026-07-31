"""Utilidades compartidas para backends de IA."""

from __future__ import annotations

import cv2
import numpy as np


def encode_png_bgra(image_bgra: np.ndarray) -> bytes:
    ok, buf = cv2.imencode(".png", image_bgra)
    if not ok:
        raise RuntimeError("No se pudo codificar el PNG de salida.")
    return buf.tobytes()


def resize_bgra(image: np.ndarray, width: int, height: int) -> np.ndarray:
    if image.shape[1] == width and image.shape[0] == height:
        return image
    interpolation = (
        cv2.INTER_AREA
        if width * height < image.shape[1] * image.shape[0]
        else cv2.INTER_LANCZOS4
    )
    return cv2.resize(image, (width, height), interpolation=interpolation)


def split_alpha(image_bgra: np.ndarray) -> tuple[np.ndarray, np.ndarray | None]:
    if image_bgra.ndim != 3 or image_bgra.shape[2] not in (3, 4):
        raise ValueError("Se espera imagen BGR o BGRA.")
    if image_bgra.shape[2] == 3:
        return image_bgra, None
    return image_bgra[:, :, :3], image_bgra[:, :, 3]


def merge_alpha(bgr: np.ndarray, alpha: np.ndarray | None) -> np.ndarray:
    if alpha is None:
        return cv2.cvtColor(bgr, cv2.COLOR_BGR2BGRA)
    if alpha.shape[:2] != bgr.shape[:2]:
        alpha = cv2.resize(alpha, (bgr.shape[1], bgr.shape[0]), interpolation=cv2.INTER_LINEAR)
    return np.dstack([bgr, alpha])


def choose_model_scale_factor(
    src_width: int,
    src_height: int,
    target_width: int | None,
    target_height: int | None,
    *,
    max_scale_factor: int = 4,
) -> int:
    """Elige el factor mínimo en {1, 2, 4} para alcanzar el tamaño objetivo."""
    max_allowed = max(1, min(4, max_scale_factor))
    if target_width is None and target_height is None:
        return min(4, max_allowed)

    aspect = src_width / src_height if src_height else 1.0
    if target_width is None and target_height is not None:
        target_width = max(1, round(target_height * aspect))
    elif target_height is None and target_width is not None:
        target_height = max(1, round(target_width / aspect))

    assert target_width is not None and target_height is not None
    needed = max(target_width / src_width, target_height / src_height)
    if needed <= 1.0:
        return 1
    if needed <= 2.0:
        return min(2, max_allowed)
    return min(4, max_allowed)


def resolve_target_size(
    src_width: int,
    src_height: int,
    target_width: int | None,
    target_height: int | None,
) -> tuple[int, int]:
    aspect = src_width / src_height if src_height else 1.0
    if target_width is None and target_height is None:
        return src_width, src_height
    if target_width is None and target_height is not None:
        return max(1, round(target_height * aspect)), target_height
    if target_height is None and target_width is not None:
        return target_width, max(1, round(target_width / aspect))
    assert target_width is not None and target_height is not None
    return target_width, target_height


def resolve_percent_size(src_width: int, src_height: int, percent: float) -> tuple[int, int]:
    """Calcula el tamaño destino como porcentaje de las dimensiones propias de la imagen."""
    factor = percent / 100.0
    return max(1, round(src_width * factor)), max(1, round(src_height * factor))
