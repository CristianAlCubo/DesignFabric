"""Backend Real-ESRGAN General x4v3 vía ONNX Runtime (CPU)."""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from designfabricv2.core.imaging.ai_upscalers.common import merge_alpha, resize_bgra, split_alpha

logger = logging.getLogger(__name__)

_TILE = 256
_OVERLAP = 16


class RealEsrganBackend:
    """Inferencia CPU con realesr-general-x4v3 (factor nativo x4)."""

    native_scale: int = 4

    def __init__(self, model_path: Path) -> None:
        self._model_path = Path(model_path)
        self._session = None

    def _ensure_session(self) -> object:
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
                f"Modelo Real-ESRGAN no encontrado: {self._model_path}. "
                "Ejecuta `uv run clearcut ensure-models` o reinicia la app."
            )

        self._session = ort.InferenceSession(
            str(self._model_path),
            providers=["CPUExecutionProvider"],
        )
        return self._session

    def upscale(self, image_bgra: np.ndarray) -> np.ndarray:
        session = self._ensure_session()
        bgr, alpha = split_alpha(image_bgra)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        upscaled_rgb = self._infer_tiled(session, rgb)
        upscaled_bgr = cv2.cvtColor(upscaled_rgb, cv2.COLOR_RGB2BGR)
        if alpha is not None:
            alpha = cv2.resize(
                alpha,
                (upscaled_bgr.shape[1], upscaled_bgr.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )
        return merge_alpha(upscaled_bgr, alpha)

    def upscale_to_factor(self, image_bgra: np.ndarray, factor: int) -> np.ndarray:
        if factor <= 1:
            return image_bgra
        upscaled = self.upscale(image_bgra)
        if factor >= self.native_scale:
            return upscaled
        target_w = max(1, round(image_bgra.shape[1] * factor))
        target_h = max(1, round(image_bgra.shape[0] * factor))
        return resize_bgra(upscaled, target_w, target_h)

    def _infer_tiled(self, session: object, rgb: np.ndarray) -> np.ndarray:
        height, width = rgb.shape[:2]
        out_h, out_w = height * self.native_scale, width * self.native_scale
        output = np.zeros((out_h, out_w, 3), dtype=np.float32)

        if height <= _TILE and width <= _TILE:
            return self._infer_chunk(session, rgb)

        step = _TILE - _OVERLAP
        for y in range(0, height, step):
            for x in range(0, width, step):
                y1 = y
                x1 = x
                y2 = min(y + _TILE, height)
                x2 = min(x + _TILE, width)
                tile = rgb[y1:y2, x1:x2]
                up_tile = self._infer_chunk(session, tile)
                oy1, ox1 = y1 * self.native_scale, x1 * self.native_scale
                oy2 = oy1 + up_tile.shape[0]
                ox2 = ox1 + up_tile.shape[1]
                output[oy1:oy2, ox1:ox2] = up_tile.astype(np.float32) / 255.0

        return np.clip(output * 255.0, 0, 255).astype(np.uint8)

    def _infer_chunk(self, session: object, rgb: np.ndarray) -> np.ndarray:
        arr = rgb.astype(np.float32) / 255.0
        arr = np.transpose(arr, (2, 0, 1))[None, ...]
        input_name = session.get_inputs()[0].name  # type: ignore[attr-defined]
        out = session.run(None, {input_name: arr})[0]  # type: ignore[attr-defined]
        out = np.squeeze(out, axis=0)
        out = np.transpose(out, (1, 2, 0))
        return np.clip(out * 255.0, 0, 255).astype(np.uint8)
