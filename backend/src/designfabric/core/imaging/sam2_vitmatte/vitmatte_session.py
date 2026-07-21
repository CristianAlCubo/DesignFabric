"""Sesión ONNX lazy para ViTMatte."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Protocol

import cv2
import numpy as np

from designfabric.core.imaging.sam2_vitmatte.preprocess import (
    bgr_to_rgb_float_nchw,
    normalize_imagenet,
    resize_long_side,
)

logger = logging.getLogger(__name__)

_VITMATTE_LONG_SIDE = 512
# El backbone ViT (patch 16) + las ramas de detalle (convstream, strides 2/4/8/16)
# de ViTMatte requieren que H y W sean múltiplos de 32; de lo contrario los
# downsamplings de cada rama redondean distinto y el Concat de fusión falla
# (p.ej. "Axis 2 has mismatched dimensions of 34 and 35").
_SIZE_MULTIPLE = 32


class VitMatteRunner(Protocol):
    def predict_alpha(self, image_bgr: np.ndarray, trimap: np.ndarray) -> np.ndarray:
        """Devuelve alpha float32 [0,1] al tamaño de la imagen de entrada del modelo."""


class VitMatteOnnxSession:
    """Inferencia ViTMatte vía onnxruntime (imagen + trimap)."""

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
                f"Modelo ViTMatte no encontrado: {self._model_path}. "
                "Configura la ruta en Ajustes → Modelos locales."
            )

        self._session = ort.InferenceSession(
            str(self._model_path),
            providers=["CPUExecutionProvider"],
        )
        logger.info("Sesión ViTMatte cargada desde %s", self._model_path)
        return self._session

    def predict_alpha(self, image_bgr: np.ndarray, trimap: np.ndarray) -> np.ndarray:
        session = self._ensure_session()
        resized_img, _ = resize_long_side(image_bgr, _VITMATTE_LONG_SIDE)
        height, width = resized_img.shape[:2]
        resized_trimap = cv2.resize(trimap, (width, height), interpolation=cv2.INTER_NEAREST)

        image_nchw = normalize_imagenet(bgr_to_rgb_float_nchw(resized_img))
        trimap_nchw = (resized_trimap.astype(np.float32) / 255.0)[None, None, ...]

        image_padded, pad_h, pad_w = self._pad_to_multiple(image_nchw)
        trimap_padded, _, _ = self._pad_to_multiple(trimap_nchw)

        feeds = self._build_feeds(session, image_padded, trimap_padded)
        outputs = session.run(None, feeds)
        alpha = self._extract_alpha(outputs, height + pad_h, width + pad_w)
        alpha = alpha[:height, :width]
        return np.clip(alpha.astype(np.float32), 0.0, 1.0)

    @staticmethod
    def _pad_to_multiple(
        tensor: np.ndarray, multiple: int = _SIZE_MULTIPLE
    ) -> tuple[np.ndarray, int, int]:
        """Rellena (reflect) H/W de un tensor NCHW hasta el múltiplo requerido."""
        height, width = tensor.shape[-2:]
        pad_h = (-height) % multiple
        pad_w = (-width) % multiple
        if pad_h == 0 and pad_w == 0:
            return tensor, 0, 0
        padded = np.pad(tensor, ((0, 0), (0, 0), (0, pad_h), (0, pad_w)), mode="reflect")
        return padded, pad_h, pad_w

    def _build_feeds(
        self,
        session: Any,
        image_nchw: np.ndarray,
        trimap_nchw: np.ndarray,
    ) -> dict[str, np.ndarray]:
        input_metas = session.get_inputs()
        names = {meta.name.lower(): meta.name for meta in input_metas}
        # ViTMatte (HF/Xenova): un solo input 4 canales = RGB normalizado + trimap.
        pixel_values_4ch = np.concatenate([image_nchw, trimap_nchw], axis=1).astype(np.float32)

        if len(input_metas) == 1:
            key = input_metas[0].name
            shape = input_metas[0].shape
            channels = shape[1] if len(shape) > 1 and isinstance(shape[1], int) else None
            # Canales dinámicos (None/'N') → asumir 4ch; solo 3ch si el modelo lo declara.
            if channels == 3:
                return {key: image_nchw.astype(np.float32)}
            return {key: pixel_values_4ch}

        image_key = self._match_name(names, ("image", "images", "pixel_values", "input_image"))
        trimap_key = self._match_name(names, ("trimap", "trimaps", "input_trimap"))
        if image_key is None:
            image_key = input_metas[0].name

        # Un input llamado pixel_values suele ser ya el tensor 4ch concatenado.
        if trimap_key is None and "pixel_values" in image_key.lower():
            return {image_key: pixel_values_4ch}

        feeds: dict[str, np.ndarray] = {image_key: image_nchw.astype(np.float32)}
        if trimap_key is not None:
            feeds[trimap_key] = trimap_nchw.astype(np.float32)
        elif len(input_metas) > 1:
            feeds[input_metas[1].name] = trimap_nchw.astype(np.float32)
        else:
            feeds[image_key] = pixel_values_4ch
        return feeds

    @staticmethod
    def _match_name(names: dict[str, str], candidates: tuple[str, ...]) -> str | None:
        for candidate in candidates:
            if candidate in names:
                return names[candidate]
        for lower, original in names.items():
            for candidate in candidates:
                if candidate in lower:
                    return original
        return None

    @staticmethod
    def _extract_alpha(outputs: list[Any], height: int, width: int) -> np.ndarray:
        if not outputs:
            raise RuntimeError("ViTMatte no produjo salidas")
        alpha = np.asarray(outputs[0], dtype=np.float32)
        alpha = np.squeeze(alpha)
        if alpha.ndim == 3:
            alpha = alpha[0]
        if alpha.shape != (height, width):
            alpha = cv2.resize(alpha, (width, height), interpolation=cv2.INTER_LINEAR).astype(np.float32)
        return alpha
