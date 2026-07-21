"""Guided Filter (He et al.) en OpenCV/numpy puro — sin opencv-contrib."""

from __future__ import annotations

import cv2
import numpy as np


def guided_filter(
    guide: np.ndarray,
    src: np.ndarray,
    *,
    radius: int = 8,
    eps: float = 1e-2,
) -> np.ndarray:
    """Filtra `src` guiado por `guide` (ambos float32 o convertibles)."""
    guide_f = _as_float(guide)
    src_f = _as_float(src)
    if guide_f.ndim == 3:
        guide_f = cv2.cvtColor(guide_f, cv2.COLOR_BGR2GRAY)
    if src_f.ndim == 3:
        src_f = cv2.cvtColor(src_f, cv2.COLOR_BGR2GRAY)

    ksize = radius * 2 + 1
    mean_i = cv2.boxFilter(guide_f, cv2.CV_32F, (ksize, ksize))
    mean_p = cv2.boxFilter(src_f, cv2.CV_32F, (ksize, ksize))
    corr_ip = cv2.boxFilter(guide_f * src_f, cv2.CV_32F, (ksize, ksize))
    corr_ii = cv2.boxFilter(guide_f * guide_f, cv2.CV_32F, (ksize, ksize))

    var_i = corr_ii - mean_i * mean_i
    cov_ip = corr_ip - mean_i * mean_p

    a = cov_ip / (var_i + eps)
    b = mean_p - a * mean_i

    mean_a = cv2.boxFilter(a, cv2.CV_32F, (ksize, ksize))
    mean_b = cv2.boxFilter(b, cv2.CV_32F, (ksize, ksize))
    return mean_a * guide_f + mean_b


def _as_float(image: np.ndarray) -> np.ndarray:
    arr = np.asarray(image)
    if arr.dtype == np.uint8:
        return arr.astype(np.float32) / 255.0
    return arr.astype(np.float32)
