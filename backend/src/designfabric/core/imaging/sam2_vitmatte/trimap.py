"""Generación de trimap a partir de una máscara binaria."""

from __future__ import annotations

import cv2
import numpy as np


def build_trimap(
    mask: np.ndarray,
    *,
    erode_iter: int = 3,
    dilate_iter: int = 6,
) -> np.ndarray:
    """Trimap uint8: 0 fondo, 128 desconocido, 255 primer plano seguro."""
    binary = (mask > 0).astype(np.uint8) * 255
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    definite_fg = cv2.erode(binary, kernel, iterations=erode_iter)
    definite_bg = cv2.dilate(binary, kernel, iterations=dilate_iter)

    trimap = np.full(binary.shape, 128, dtype=np.uint8)
    trimap[definite_bg == 0] = 0
    trimap[definite_fg == 255] = 255
    return trimap
