"""Pipeline de eliminación de fondo para ilustraciones tipo sticker/clipart/DTF.

Flujo orquestado por :func:`process_image`:

    load_image -> strategy.generate_mask -> iterative_erode -> apply_mask -> save_image
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from designfabricv2.core.imaging.silhouette_strategies import SilhouetteStrategy

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True, slots=True)
class RemovalConfig:
    """Configuración inmutable del pipeline de eliminación de fondo."""

    max_iterations: int = 5
    """Número máximo de erosiones iterativas hasta estabilizar el área de la máscara."""


def load_image(image_path: Path) -> np.ndarray:
    """Carga una imagen PNG/JPG/WEBP desde disco en BGR uint8."""
    if not image_path.is_file():
        raise FileNotFoundError(f"No existe el archivo de entrada: {image_path}")
    if image_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Formato no soportado '{image_path.suffix}'. "
            f"Formatos soportados: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    img = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"No se pudo leer la imagen: {image_path}")
    return img


def iterative_erode(mask: np.ndarray, max_iterations: int = 5) -> np.ndarray:
    """Erosiona la máscara hasta que el área se estabilice o se agoten las iteraciones."""
    current_mask = mask
    previous_area = cv2.countNonZero(current_mask)
    kernel = np.ones((3, 3), np.uint8)

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


def save_image(image: np.ndarray, output_path: Path) -> None:
    """Guarda una imagen BGRA como PNG, creando directorios de salida si hace falta."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), image):
        raise OSError(f"No se pudo guardar la imagen: {output_path}")


class StickerProcessor:
    """Contexto del Strategy: aplica detección de silueta y postproceso de erosión."""

    def __init__(self, strategy: SilhouetteStrategy) -> None:
        self.strategy = strategy

    def set_strategy(self, strategy: SilhouetteStrategy) -> None:
        self.strategy = strategy

    def process(
        self,
        image_path: Path,
        output_path: Path,
        config: RemovalConfig = RemovalConfig(),
    ) -> np.ndarray:
        img = load_image(image_path)
        mask = self.strategy.generate_mask(img)
        mask = iterative_erode(mask, config.max_iterations)
        if not np.any(mask):
            logger.warning("La máscara quedó completamente transparente para %s.", image_path)
        result = apply_mask(img, mask)
        save_image(result, output_path)
        return result


def process_image(
    input_path: Path,
    output_path: Path,
    strategy: SilhouetteStrategy,
    config: RemovalConfig = RemovalConfig(),
) -> np.ndarray:
    """Orquesta el pipeline completo de eliminación de fondo y guarda el resultado."""
    return StickerProcessor(strategy).process(input_path, output_path, config)
