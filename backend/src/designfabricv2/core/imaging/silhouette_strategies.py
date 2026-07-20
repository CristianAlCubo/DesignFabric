"""Estrategias de detección de silueta para ilustraciones tipo sticker.

Implementa el patrón Strategy: cada estrategia genera una máscara binaria
``uint8`` (0 = fondo, 255 = sujeto) a partir de una imagen BGR.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal

import cv2
import numpy as np

StrategyName = Literal["white_background", "color_background"]


class SilhouetteStrategy(ABC):
    """Genera una máscara de silueta a partir de una imagen BGR."""

    @abstractmethod
    def generate_mask(self, img: np.ndarray) -> np.ndarray:
        """Devuelve una máscara binaria uint8 de forma (H, W)."""


class WhiteBackgroundStrategy(SilhouetteStrategy):
    """Estrategia rápida: ideal para fondos blancos limpios."""

    def generate_mask(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        return self._extract_largest_contour(thresh)

    def _extract_largest_contour(self, thresh: np.ndarray) -> np.ndarray:
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        mask = np.zeros(thresh.shape, dtype=np.uint8)
        if contours:
            largest = max(contours, key=cv2.contourArea)
            cv2.drawContours(mask, [largest], -1, 255, -1)
        return mask


class ColorBackgroundStrategy(SilhouetteStrategy):
    """Estrategia robusta: detecta el color predominante en las esquinas."""

    def generate_mask(self, img: np.ndarray) -> np.ndarray:
        height, width = img.shape[:2]
        corners = [
            img[0:5, 0:5],
            img[height - 5 : height, 0:5],
            img[0:5, width - 5 : width],
            img[height - 5 : height, width - 5 : width],
        ]
        background_color = np.mean([np.mean(corner, axis=(0, 1)) for corner in corners], axis=0)
        background_color_bgr = np.asarray(background_color, dtype=np.uint8)

        diff = cv2.absdiff(img, background_color_bgr)
        diff_gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
        _, mask = cv2.threshold(diff_gray, 30, 255, cv2.THRESH_BINARY)

        kernel = np.ones((5, 5), np.uint8)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


_STRATEGIES: dict[StrategyName, type[SilhouetteStrategy]] = {
    "white_background": WhiteBackgroundStrategy,
    "color_background": ColorBackgroundStrategy,
}


def create_silhouette_strategy(name: StrategyName) -> SilhouetteStrategy:
    """Crea una estrategia de silueta por nombre."""
    try:
        strategy_cls = _STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(
            f"Estrategia desconocida '{name}'. "
            f"Opciones: {sorted(_STRATEGIES)}"
        ) from exc
    return strategy_cls()
