"""Postprocesado final: alpha + BGR → BGRA."""

from __future__ import annotations

import cv2
import numpy as np


def upscale_alpha(alpha: np.ndarray, width: int, height: int) -> np.ndarray:
    """Redimensiona alpha float/uint8 a (height, width)."""
    if alpha.shape[0] == height and alpha.shape[1] == width:
        return alpha
    interpolation = cv2.INTER_LINEAR
    return cv2.resize(alpha, (width, height), interpolation=interpolation)


def compose_bgra(image_bgr: np.ndarray, alpha: np.ndarray) -> np.ndarray:
    """Combina BGR uint8 con alpha (float [0,1] o uint8) en BGRA uint8."""
    if alpha.dtype != np.uint8:
        alpha_u8 = np.clip(np.rint(alpha * 255.0), 0, 255).astype(np.uint8)
    else:
        alpha_u8 = alpha
    b, g, r = cv2.split(image_bgr)
    return cv2.merge([b, g, r, alpha_u8])


def refine_alpha_edges(alpha: np.ndarray) -> np.ndarray:
    """Suavizado ligero de bordes del alpha float [0,1]."""
    blurred = cv2.GaussianBlur(alpha.astype(np.float32), (0, 0), sigmaX=0.8)
    return np.clip(blurred, 0.0, 1.0)
