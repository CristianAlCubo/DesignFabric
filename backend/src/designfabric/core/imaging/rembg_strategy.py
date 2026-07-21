"""Estrategia de eliminación de fondo usando la librería `rembg` (modelo IS-Net-anime).

`rembg` empaqueta el modelo IS-Net entrenado específicamente sobre arte anime/2D
(sesión `"isnet-anime"`), descargado y cacheado automáticamente en el primer uso
(vía `pooch`, requiere internet esa primera vez). No requiere configurar rutas en
Ajustes → Modelos locales.
"""

from __future__ import annotations

import logging
from typing import Any

import cv2
import numpy as np

from designfabric.core.imaging.background_removal_strategies import BackgroundRemovalStrategy

logger = logging.getLogger(__name__)

_SESSION_NAME = "isnet-anime"


class RembgIllustrationStrategy(BackgroundRemovalStrategy):
    """Segmentación de un solo paso vía `rembg` (IS-Net-anime), sin alpha matting.

    `alpha_matting=False` por defecto: IS-Net-anime ya da bordes duros/consistentes
    propios de arte 2D; el post-proceso `pymatting` de rembg está pensado para
    degradados fotográficos (pelo, desenfoque) y puede introducir semitransparencia
    no deseada sobre flat color.
    """

    def __init__(self) -> None:
        self._session: Any | None = None

    def _ensure_session(self) -> Any:
        if self._session is not None:
            return self._session
        try:
            from rembg import new_session  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "rembg no está instalado. Ejecuta `uv sync` e inténtalo de nuevo."
            ) from exc

        self._session = new_session(_SESSION_NAME)
        logger.info("Sesión rembg cargada (%s)", _SESSION_NAME)
        return self._session

    def remove_background(self, image: np.ndarray) -> np.ndarray:
        from rembg import remove

        session = self._ensure_session()
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        rgba = remove(rgb, session=session, alpha_matting=False)
        rgba = np.asarray(rgba)

        r, g, b, a = cv2.split(rgba)
        return cv2.merge([b, g, r, a])
