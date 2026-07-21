"""Operaciones auxiliares compartidas por estrategias clásicas de eliminación de fondo."""

from __future__ import annotations

import cv2
import numpy as np


def extract_largest_contour(thresh: np.ndarray) -> np.ndarray:
    """Devuelve una máscara binaria con solo el contorno externo de mayor área."""
    contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    mask = np.zeros(thresh.shape, dtype=np.uint8)
    if contours:
        largest = max(contours, key=cv2.contourArea)
        cv2.drawContours(mask, [largest], -1, 255, -1)
    return mask


def iterative_erode(mask: np.ndarray, max_iterations: int = 5) -> np.ndarray:
    """Erosiona la máscara hasta que el área se estabilice o se agoten las iteraciones."""
    current_mask = mask
    previous_area = cv2.countNonZero(current_mask)
    kernel = np.ones((3, 3), dtype=np.uint8)

    for _ in range(1, max_iterations + 1):
        eroded_mask = cv2.erode(current_mask, kernel, iterations=1)
        current_area = cv2.countNonZero(eroded_mask)

        if current_area == 0 or (previous_area - current_area) < (previous_area * 0.005):
            break
        current_mask = eroded_mask
        previous_area = current_area

    return current_mask


def apply_mask(img: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """Combina la imagen BGR con la máscara en un array BGRA."""
    b, g, r = cv2.split(img)
    return cv2.merge([b, g, r, mask])
