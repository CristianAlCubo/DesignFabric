"""Backend SPAN vía PyTorch + Spandrel (GPU CUDA).

Desactivado por ahora: no se registra en las estrategias de escalado ni en la UI.
Se conserva el módulo por si se reactiva más adelante.
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from designfabricv2.core.imaging.ai_upscalers.common import merge_alpha, resize_bgra, split_alpha

logger = logging.getLogger(__name__)


class SpanBackend:
    """Inferencia SPAN con checkpoints x2/x4 cargados por Spandrel."""

    def __init__(self, x2_path: Path, x4_path: Path) -> None:
        self._x2_path = Path(x2_path)
        self._x4_path = Path(x4_path)
        self._models: dict[int, object] = {}

    def _load_model(self, scale: int) -> object:
        if scale in self._models:
            return self._models[scale]

        path = self._x2_path if scale == 2 else self._x4_path
        if not path.is_file():
            if scale == 2 and self._x4_path.is_file():
                logger.info("Checkpoint SPAN x2 ausente; se usará x4 + downscale.")
                return self._load_model(4)
            raise RuntimeError(
                f"Modelo SPAN no encontrado: {path}. "
                "Ejecuta `uv run clearcut ensure-models` o reinicia la app."
            )

        try:
            import torch  # type: ignore[import-not-found]
            from spandrel import ImageModelDescriptor, ModelLoader  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "torch/spandrel no están instalados. Ejecuta `uv sync` e inténtalo de nuevo."
            ) from exc

        if not torch.cuda.is_available():
            raise RuntimeError("SPAN requiere GPU CUDA disponible.")

        model = ModelLoader().load_from_file(str(path))
        if not isinstance(model, ImageModelDescriptor):
            raise RuntimeError(f"El archivo {path} no es un modelo de imagen Spandrel.")

        model.cuda().eval()
        self._models[scale] = model
        return model

    def upscale_to_factor(self, image_bgra: np.ndarray, factor: int) -> np.ndarray:
        if factor <= 1:
            return image_bgra

        model_scale = 2 if factor <= 2 else 4
        try:
            model = self._load_model(model_scale)
            used_scale = model_scale
        except RuntimeError:
            if model_scale == 2:
                model = self._load_model(4)
                used_scale = 4
            else:
                raise

        upscaled = self._infer(model, image_bgra)
        if factor < used_scale:
            target_w = max(1, round(image_bgra.shape[1] * factor))
            target_h = max(1, round(image_bgra.shape[0] * factor))
            return resize_bgra(upscaled, target_w, target_h)
        return upscaled

    def _infer(self, model: object, image_bgra: np.ndarray) -> np.ndarray:
        import torch  # type: ignore[import-not-found]

        bgr, alpha = split_alpha(image_bgra)
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        tensor = (
            torch.from_numpy(rgb.astype(np.float32) / 255.0)
            .permute(2, 0, 1)
            .unsqueeze(0)
            .cuda()
        )

        with torch.inference_mode():
            out = model(tensor)  # type: ignore[operator]

        out_np = (
            out.squeeze(0)
            .clamp(0, 1)
            .permute(1, 2, 0)
            .detach()
            .cpu()
            .numpy()
        )
        out_rgb = np.clip(out_np * 255.0, 0, 255).astype(np.uint8)
        out_bgr = cv2.cvtColor(out_rgb, cv2.COLOR_RGB2BGR)
        if alpha is not None:
            alpha = cv2.resize(
                alpha,
                (out_bgr.shape[1], out_bgr.shape[0]),
                interpolation=cv2.INTER_LINEAR,
            )
        return merge_alpha(out_bgr, alpha)
