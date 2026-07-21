"""Estrategias de eliminación de fondo (patrón Strategy).

Contrato público: BGR uint8 → BGRA uint8. La detección de silueta es una fase
interna de algunas estrategias clásicas, no la interfaz del dominio.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from designfabric.core.imaging.background_removal_ops import (
    apply_mask,
    extract_largest_contour,
    iterative_erode,
)

StrategyName = Literal[
    "white_background",
    "color_background",
    "sam2_vitmatte",
    "isnet_general",
    "rembg_illustration",
    "birefnet_sam2_matte",
]


@dataclass(frozen=True, slots=True)
class RemovalModelPaths:
    """Rutas locales a los ONNX usados por las estrategias neurales.

    Cada campo es opcional porque cada estrategia requiere un subconjunto
    distinto; la validación de qué campos hacen falta vive en
    `create_background_removal_strategy`.
    """

    sam2_encoder_onnx: Path | None = None
    sam2_decoder_onnx: Path | None = None
    vitmatte_onnx: Path | None = None
    isnet_general_onnx: Path | None = None


class BackgroundRemovalStrategy(ABC):
    """Elimina el fondo de una imagen y devuelve BGRA uint8."""

    @abstractmethod
    def remove_background(self, image: np.ndarray) -> np.ndarray:
        """Recibe BGR uint8 y devuelve BGRA uint8."""


class WhiteBackgroundStrategy(BackgroundRemovalStrategy):
    """Estrategia rápida: ideal para fondos blancos limpios."""

    def __init__(self, max_iterations: int = 5) -> None:
        self._max_iterations = max_iterations

    def remove_background(self, image: np.ndarray) -> np.ndarray:
        mask = self._detect_silhouette(image)
        mask = iterative_erode(mask, self._max_iterations)
        return apply_mask(image, mask)

    def _detect_silhouette(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY_INV)
        return extract_largest_contour(thresh)


class ColorBackgroundStrategy(BackgroundRemovalStrategy):
    """Estrategia robusta: detecta el color predominante en las esquinas."""

    def __init__(self, max_iterations: int = 5) -> None:
        self._max_iterations = max_iterations

    def remove_background(self, image: np.ndarray) -> np.ndarray:
        mask = self._detect_silhouette(image)
        mask = iterative_erode(mask, self._max_iterations)
        return apply_mask(image, mask)

    def _detect_silhouette(self, img: np.ndarray) -> np.ndarray:
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

        kernel = np.ones((5, 5), dtype=np.uint8)
        return cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)


_CLASSIC_STRATEGIES: dict[str, type[BackgroundRemovalStrategy]] = {
    "white_background": WhiteBackgroundStrategy,
    "color_background": ColorBackgroundStrategy,
}


def create_background_removal_strategy(
    name: StrategyName,
    *,
    model_paths: RemovalModelPaths | None = None,
    max_iterations: int = 5,
) -> BackgroundRemovalStrategy:
    """Crea una estrategia de eliminación de fondo por nombre."""
    if name == "sam2_vitmatte":
        from designfabric.core.imaging.sam2_vitmatte import Sam2VitMatteStrategy

        if model_paths is None or not (
            model_paths.sam2_encoder_onnx and model_paths.sam2_decoder_onnx and model_paths.vitmatte_onnx
        ):
            raise ValueError(
                "La estrategia 'sam2_vitmatte' requiere rutas a los modelos ONNX "
                "(SAM2 encoder, SAM2 decoder y ViTMatte). "
                "Configúralas en Ajustes → Modelos locales."
            )
        return Sam2VitMatteStrategy(model_paths)

    if name == "isnet_general":
        from designfabric.core.imaging.isnet_strategy import IsNetGeneralStrategy

        if model_paths is None or model_paths.isnet_general_onnx is None:
            raise ValueError(
                "La estrategia 'isnet_general' requiere la ruta al modelo ONNX IS-Net. "
                "Configúrala en Ajustes → Modelos locales."
            )
        return IsNetGeneralStrategy(model_paths.isnet_general_onnx)

    if name == "rembg_illustration":
        from designfabric.core.imaging.rembg_strategy import RembgIllustrationStrategy

        return RembgIllustrationStrategy()

    if name == "birefnet_sam2_matte":
        from designfabric.core.imaging.birefnet_sam2_matte_strategy import BiRefNetSam2MatteStrategy

        return BiRefNetSam2MatteStrategy(model_paths or RemovalModelPaths())

    try:
        strategy_cls = _CLASSIC_STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(
            f"Estrategia desconocida '{name}'. "
            f"Opciones: {sorted([
                *_CLASSIC_STRATEGIES,
                'sam2_vitmatte',
                'isnet_general',
                'rembg_illustration',
                'birefnet_sam2_matte',
            ])}"
        ) from exc
    return strategy_cls(max_iterations=max_iterations)
