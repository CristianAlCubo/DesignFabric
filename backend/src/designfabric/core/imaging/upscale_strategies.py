"""Estrategias de escalado (patrón Strategy)."""

from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from designfabric.core.imaging.ai_upscalers.common import (
    choose_model_scale_factor,
    encode_png_bgra,
    resize_bgra,
    resolve_target_size,
)
from designfabric.core.imaging.ai_upscalers.realesrgan import RealEsrganBackend
from designfabric.core.imaging.upscale_config import UpscaleConfig
from designfabric.core.imaging.vector_engine import ExportConfig, TraceConfig, VectorEngine, VectorEngineError

# Auto y SPAN desactivados; ver historial / ai_upscalers/span.py
UpscaleStrategyName = Literal["vector", "realesrgan"]

SCALE_STRATEGY_META: tuple[dict[str, str], ...] = (
    {
        "id": "realesrgan",
        "label": "Real-ESRGAN (CPU)",
        "description": "Real-ESRGAN General x4v3 vía ONNX; buen equilibrio calidad/velocidad en CPU.",
    },
    {
        "id": "vector",
        "label": "Vectorial (SVG)",
        "description": "Vectoriza con VTracer y rasteriza a alta resolución (máxima fidelidad).",
    },
)


class UpscaleError(Exception):
    """Error en una estrategia de escalado."""


@dataclass(frozen=True)
class UpscaleRequest:
    """Entrada normalizada para cualquier estrategia de escalado."""

    image_bgra: np.ndarray | None
    png_bytes: bytes | None
    svg_text: str | None
    input_suffix: str
    target_width: int | None
    target_height: int | None
    dpi: float
    trace: TraceConfig
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


class VectorUpscaleStrategy(UpscaleStrategy):
    """Escalado profesional vía VTracer + CairoSVG."""

    name = "vector"

    def upscale(self, request: UpscaleRequest) -> UpscaleResult:
        started = time.perf_counter()
        engine = VectorEngine(request.trace)
        export = ExportConfig(
            width_px=request.target_width,
            height_px=request.target_height,
            dpi=request.dpi,
        )

        if request.svg_text is not None:
            png_bytes = engine.rasterize(request.svg_text, export)
            source_size = _svg_source_size(request.svg_text)
        elif request.png_bytes is not None:
            source_size = _png_size(request.png_bytes, request.image_bgra)
            png_bytes = engine.process(request.png_bytes, export)
        else:
            raise UpscaleError("La estrategia vectorial requiere PNG o SVG de entrada.")

        final = _png_size(png_bytes, None)
        factor = (
            max(final[0] / source_size[0], final[1] / source_size[1])
            if source_size[0] and source_size[1]
            else 1.0
        )
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return UpscaleResult(
            png_bytes=png_bytes,
            backend=self.name,
            device="cpu",
            scale_factor=factor,
            source_size=source_size,
            final_size=final,
            inference_ms=elapsed_ms,
        )


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
    "vector": VectorUpscaleStrategy,
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


def _png_size(png_bytes: bytes, image_bgra: np.ndarray | None) -> tuple[int, int]:
    if image_bgra is not None:
        return image_bgra.shape[1], image_bgra.shape[0]
    arr = np.frombuffer(png_bytes, dtype=np.uint8)
    decoded = cv2.imdecode(arr, cv2.IMREAD_UNCHANGED)
    if decoded is None:
        raise UpscaleError("No se pudo leer el tamaño del PNG.")
    return decoded.shape[1], decoded.shape[0]


def _svg_source_size(svg_text: str) -> tuple[int, int]:
    from designfabric.core.imaging.vector_engine import _parse_svg_size

    try:
        width, height = _parse_svg_size(svg_text)
    except VectorEngineError:
        return (1, 1)
    return max(1, round(width)), max(1, round(height))
