"""Pipeline de eliminación de fondo para imágenes generales.

Flujo orquestado por :func:`process_image`:

    load_image -> strategy.remove_background -> save_image
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from designfabric.core.imaging.background_removal_strategies import BackgroundRemovalStrategy

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


@dataclass(frozen=True, slots=True)
class RemovalConfig:
    """Configuración inmutable del pipeline de eliminación de fondo."""

    max_iterations: int = 5
    """Número máximo de erosiones iterativas (estrategias clásicas por silueta)."""


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


def save_image(image: np.ndarray, output_path: Path) -> None:
    """Guarda una imagen BGRA como PNG, creando directorios de salida si hace falta."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if not cv2.imwrite(str(output_path), image):
        raise OSError(f"No se pudo guardar la imagen: {output_path}")


class BackgroundRemover:
    """Contexto del Strategy: carga, delega la eliminación de fondo y guarda el resultado."""

    def __init__(self, strategy: BackgroundRemovalStrategy) -> None:
        self.strategy = strategy

    def set_strategy(self, strategy: BackgroundRemovalStrategy) -> None:
        self.strategy = strategy

    def process(
        self,
        image_path: Path,
        output_path: Path,
        config: RemovalConfig = RemovalConfig(),
    ) -> np.ndarray:
        del config  # la erosión/postproceso vive dentro de cada estrategia
        img = load_image(image_path)
        result = self.strategy.remove_background(img)
        if result.ndim != 3 or result.shape[2] != 4:
            raise ValueError(
                f"La estrategia debe devolver BGRA uint8; se obtuvo shape={result.shape}"
            )
        if not np.any(result[:, :, 3]):
            logger.warning("El resultado quedó completamente transparente para %s.", image_path)
        save_image(result, output_path)
        return result


def process_image(
    input_path: Path,
    output_path: Path,
    strategy: BackgroundRemovalStrategy,
    config: RemovalConfig = RemovalConfig(),
) -> np.ndarray:
    """Orquesta el pipeline completo de eliminación de fondo y guarda el resultado."""
    return BackgroundRemover(strategy).process(input_path, output_path, config)
