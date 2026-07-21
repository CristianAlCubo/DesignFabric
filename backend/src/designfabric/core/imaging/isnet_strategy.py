"""Estrategia de eliminación de fondo basada en IS-Net (general-use), estilo rembg.

Segmentación de un solo paso (sin trimap ni matting): a diferencia de
`sam2_vitmatte` (pensado para fotos con bordes suaves), esta estrategia da
bordes duros y consistentes — la opción más fiable para ilustraciones/stickers
de arte plano. Arquitectura U-Net (skips a la misma resolución en todas las
ramas), por lo que el resize directo a 1024×1024 no puede sufrir el mismatch
de Concat que afecta a arquitecturas con ramas de distinto stride.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from designfabric.core.imaging.background_removal_ops import apply_mask
from designfabric.core.imaging.background_removal_strategies import BackgroundRemovalStrategy

logger = logging.getLogger(__name__)

_INPUT_SIZE = 1024
_MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 3, 1, 1)
_STD = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 3, 1, 1)


class IsNetGeneralStrategy(BackgroundRemovalStrategy):
    """Inferencia ONNX IS-Net general-use: un forward pass, sin matting."""

    def __init__(self, model_path: Path) -> None:
        self._model_path = Path(model_path)
        self._session: Any | None = None

    def _ensure_session(self) -> Any:
        if self._session is not None:
            return self._session
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]
        except ImportError as exc:
            raise RuntimeError(
                "onnxruntime no está instalado. Ejecuta `uv sync` e inténtalo de nuevo."
            ) from exc

        if not self._model_path.is_file():
            raise RuntimeError(
                f"Modelo IS-Net no encontrado: {self._model_path}. "
                "Configura la ruta en Ajustes → Modelos locales."
            )

        self._session = ort.InferenceSession(
            str(self._model_path),
            providers=["CPUExecutionProvider"],
        )
        logger.info("Sesión IS-Net cargada desde %s", self._model_path)
        return self._session

    def remove_background(self, image: np.ndarray) -> np.ndarray:
        session = self._ensure_session()
        orig_h, orig_w = image.shape[:2]

        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        resized = cv2.resize(rgb, (_INPUT_SIZE, _INPUT_SIZE), interpolation=cv2.INTER_LINEAR)
        nchw = np.transpose(resized.astype(np.float32) / 255.0, (2, 0, 1))[None, ...]
        nchw = (nchw - _MEAN) / _STD

        input_name = session.get_inputs()[0].name
        outputs = session.run(None, {input_name: nchw.astype(np.float32)})
        pred = self._extract_prediction(outputs)

        alpha = cv2.resize(pred, (orig_w, orig_h), interpolation=cv2.INTER_LINEAR)
        alpha_u8 = np.clip(np.rint(np.clip(alpha, 0.0, 1.0) * 255.0), 0, 255).astype(np.uint8)
        return apply_mask(image, alpha_u8)

    @staticmethod
    def _extract_prediction(outputs: list[Any]) -> np.ndarray:
        if not outputs:
            raise RuntimeError("IS-Net no produjo salidas")
        pred = np.asarray(outputs[0], dtype=np.float32)
        pred = np.squeeze(pred)
        if pred.ndim == 3:
            pred = pred[0]
        if pred.ndim != 2:
            raise RuntimeError(f"Forma de salida IS-Net no soportada: {pred.shape}")

        low, high = float(pred.min()), float(pred.max())
        if high - low > 1e-6:
            pred = (pred - low) / (high - low)
        else:
            pred = np.zeros_like(pred)
        return pred
