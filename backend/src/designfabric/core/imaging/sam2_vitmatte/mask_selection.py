"""Selección y limpieza geométrica de máscaras SAM2."""

from __future__ import annotations

import cv2
import numpy as np


def select_primary_mask(masks: np.ndarray) -> np.ndarray:
    """Elige la máscara de mayor área entre candidatos (bool/float/uint8)."""
    arr = np.asarray(masks)
    if arr.ndim == 2:
        candidates = [arr]
    elif arr.ndim == 3:
        candidates = [arr[i] for i in range(arr.shape[0])]
    elif arr.ndim == 4:
        # [N, 1, H, W] o [1, N, H, W]
        if arr.shape[1] == 1:
            candidates = [arr[i, 0] for i in range(arr.shape[0])]
        else:
            candidates = [arr[0, i] for i in range(arr.shape[1])]
    else:
        raise ValueError(f"Forma de máscaras no soportada: {arr.shape}")

    best: np.ndarray | None = None
    best_area = -1
    for candidate in candidates:
        binary = _to_binary(candidate)
        area = int(cv2.countNonZero(binary))
        if area > best_area:
            best_area = area
            best = binary
    if best is None:
        raise ValueError("No hay máscaras candidatas")
    return best


def clean_mask(mask: np.ndarray, close_kernel: int = 5, open_kernel: int = 3) -> np.ndarray:
    """Limpieza morfológica y conservación del mayor componente conexo."""
    binary = _to_binary(mask)
    if close_kernel > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_kernel, close_kernel))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, k)
    if open_kernel > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (open_kernel, open_kernel))
        binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, k)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    if num_labels <= 1:
        return binary
    largest_label = 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))
    cleaned = np.zeros_like(binary)
    cleaned[labels == largest_label] = 255
    return cleaned


def _to_binary(mask: np.ndarray) -> np.ndarray:
    arr = np.squeeze(mask)
    if arr.dtype == np.bool_:
        return (arr.astype(np.uint8)) * 255
    if np.issubdtype(arr.dtype, np.floating):
        return (arr > 0.5).astype(np.uint8) * 255
    return (arr > 0).astype(np.uint8) * 255
