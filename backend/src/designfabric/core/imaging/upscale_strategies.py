"""Estrategias de escalado (patrón Strategy)."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np

from designfabric.core.imaging.ai_upscalers.common import (
    choose_model_scale_factor,
    encode_png_bgra,
    resize_bgra,
    resolve_target_size,
)
from designfabric.core.imaging.ai_upscalers.realesrgan import RealEsrganBackend
from designfabric.core.imaging.upscale_config import UpscaleConfig

# Auto y SPAN desactivados; ver historial / ai_upscalers/span.py
UpscaleStrategyName = Literal["realesrgan"]

SCALE_STRATEGY_META: tuple[dict[str, str], ...] = (
    {
        "id": "realesrgan",
        "label": "Real-ESRGAN (CPU)",
        "description": "Real-ESRGAN General x4v3 vía ONNX; buen equilibrio calidad/velocidad en CPU.",
    },
)


class UpscaleError(Exception):
    """Error en una estrategia de escalado."""


@dataclass(frozen=True)
class UpscaleRequest:
    """Entrada normalizada para cualquier estrategia de escalado."""

    image_bgra: np.ndarray | None
    png_bytes: bytes | None
    input_suffix: str
    target_width: int | None
    target_height: int | None
    config: UpscaleConfig
    project_root: Path | None = None


@dataclass(frozen=True)
class UpscaleResult:
    """Salida de una estrategia de escalado."""

    png_bytes: bytes
    backend: str
    device: str
    scale_factor: float
    source_size: tuple[int, int]
    final_size: tuple[int, int]
    inference_ms: float
    warning: str | None = None


class UpscaleStrategy(ABC):
    """Interfaz común de backends de escalado."""

    name: str

    @abstractmethod
    def upscale(self, request: UpscaleRequest) -> UpscaleResult:
        """Escala la imagen al tamaño objetivo."""


class RealEsrganUpscaleStrategy(UpscaleStrategy):
    """Super-resolución Real-ESRGAN General x4v3 en CPU."""

    name = "realesrgan"

    def __init__(self, backend: RealEsrganBackend | None = None) -> None:
        self._backend = backend

    def upscale(self, request: UpscaleRequest) -> UpscaleResult:
        if request.image_bgra is None:
            raise UpscaleError("Real-ESRGAN requiere una imagen raster (PNG).")

        started = time.perf_counter()
        image = request.image_bgra
        src_h, src_w = image.shape[:2]
        tw, th = resolve_target_size(src_w, src_h, request.target_width, request.target_height)
        factor = choose_model_scale_factor(
            src_w,
            src_h,
            tw,
            th,
            max_scale_factor=request.config.max_scale_factor,
        )

        if max(src_w, src_h) > request.config.max_image_side:
            raise UpscaleError(
                f"Imagen demasiado grande ({src_w}x{src_h}); "
                f"máximo lado {request.config.max_image_side}."
            )

        backend = self._backend or RealEsrganBackend(
            request.config.models_path(request.project_root) / request.config.realesrgan_model
        )

        if factor == 1:
            out = resize_bgra(image, tw, th) if (src_w, src_h) != (tw, th) else image
        else:
            out = backend.upscale_to_factor(image, factor)
            out = resize_bgra(out, tw, th)

        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return UpscaleResult(
            png_bytes=encode_png_bgra(out),
            backend=self.name,
            device="cpu",
            scale_factor=float(factor),
            source_size=(src_w, src_h),
            final_size=(out.shape[1], out.shape[0]),
            inference_ms=elapsed_ms,
        )


# class AutoUpscaleStrategy — desactivado


_STRATEGIES: dict[UpscaleStrategyName, type[UpscaleStrategy]] = {
    "realesrgan": RealEsrganUpscaleStrategy,
}


def create_upscale_strategy(name: UpscaleStrategyName) -> UpscaleStrategy:
    """Crea una estrategia de escalado por nombre."""
    try:
        strategy_cls = _STRATEGIES[name]
    except KeyError as exc:
        raise ValueError(
            f"Estrategia de escalado desconocida '{name}'. "
            f"Opciones: {sorted(_STRATEGIES)}"
        ) from exc
    return strategy_cls()
