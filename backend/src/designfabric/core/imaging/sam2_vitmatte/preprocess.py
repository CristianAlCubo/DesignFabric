"""Preprocesado de imagen para SAM2 / ViTMatte."""

from __future__ import annotations

import cv2
import numpy as np


def resize_long_side(image: np.ndarray, long_side: int) -> tuple[np.ndarray, float]:
    """Redimensiona manteniendo aspecto; devuelve (imagen, escala respecto al original)."""
    height, width = image.shape[:2]
    current_long = max(height, width)
    if current_long == 0:
        raise ValueError("Imagen vacía")
    scale = long_side / current_long
    if abs(scale - 1.0) < 1e-6:
        return image.copy(), 1.0
    new_w = max(1, int(round(width * scale)))
    new_h = max(1, int(round(height * scale)))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    return resized, scale


def bgr_to_rgb_float_nchw(image_bgr: np.ndarray) -> np.ndarray:
    """BGR uint8 → float32 NCHW RGB en [0, 1]."""
    rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return np.transpose(rgb, (2, 0, 1))[None, ...]


def normalize_imagenet(nchw: np.ndarray) -> np.ndarray:
    """Normalización ImageNet sobre tensor NCHW RGB [0, 1]."""
    mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
    std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)
    return (nchw - mean) / std
