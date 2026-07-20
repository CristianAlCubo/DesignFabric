"""Orquestación del escalado: I/O, fallbacks y logging."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from designfabric.core.imaging.ai_upscalers.common import encode_png_bgra
from designfabric.core.imaging.model_assets import ensure_models_for_strategy
from designfabric.core.imaging.upscale_config import UpscaleConfig, load_upscale_config
from designfabric.core.imaging.upscale_strategies import (
    SCALE_STRATEGY_META,
    UpscaleError,
    UpscaleRequest,
    UpscaleResult,
    UpscaleStrategy,
    UpscaleStrategyName,
    create_upscale_strategy,
)

logger = logging.getLogger(__name__)

WARNING_PREFIX = "CLEARCUT_WARNING:"


@dataclass(frozen=True)
class ScaleOutcome:
    """Resultado de `scale_image` incluyendo metadata y avisos."""

    output_path: Path
    result: UpscaleResult


def get_scale_defaults() -> dict:
    """Defaults de escalado para UI/bridge (estrategias + config)."""
    config = load_upscale_config()
    return {
        "default_strategy": "realesrgan",
        "strategies": [dict(item) for item in SCALE_STRATEGY_META],
        "config": config.to_dict(),
    }


def scale_image(
    input_path: Path,
    output_path: Path,
    *,
    strategy: UpscaleStrategyName = "realesrgan",
    width: int | None = None,
    height: int | None = None,
    config: UpscaleConfig | None = None,
    project_root: Path | None = None,
    strategy_impl: UpscaleStrategy | None = None,
) -> ScaleOutcome:
    """Escala una imagen con la estrategia indicada y escribe el PNG de salida."""
    path = Path(input_path)
    if not path.is_file():
        raise UpscaleError(f"No existe el archivo de entrada: {path}")

    suffix = path.suffix.lower()
    cfg = config or load_upscale_config()
    root = project_root or _find_project_root(path)

    ensure_models_for_strategy(strategy, config=cfg, project_root=root)

    request = _build_request(
        path=path,
        suffix=suffix,
        width=width,
        height=height,
        config=cfg,
        project_root=root,
    )

    selected = strategy_impl or create_upscale_strategy(strategy)
    result = _run_with_fallback(selected, request, strategy)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(result.png_bytes)

    _log_result(result)
    return ScaleOutcome(output_path=out, result=result)


def _build_request(
    *,
    path: Path,
    suffix: str,
    width: int | None,
    height: int | None,
    config: UpscaleConfig,
    project_root: Path | None,
) -> UpscaleRequest:
    if suffix != ".png":
        raise UpscaleError("El escalado requiere un PNG de entrada.")

    png_bytes = path.read_bytes()
    image = cv2.imdecode(np.frombuffer(png_bytes, dtype=np.uint8), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise UpscaleError(f"No se pudo decodificar el PNG: {path}")
    if image.ndim == 2:
        image = cv2.cvtColor(image, cv2.COLOR_GRAY2BGRA)
    elif image.shape[2] == 3:
        image = cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)

    return UpscaleRequest(
        image_bgra=image,
        png_bytes=png_bytes,
        input_suffix=suffix,
        target_width=width,
        target_height=height,
        config=config,
        project_root=project_root,
    )


def _run_with_fallback(
    strategy: UpscaleStrategy,
    request: UpscaleRequest,
    requested_name: UpscaleStrategyName,
) -> UpscaleResult:
    try:
        return strategy.upscale(request)
    except Exception as primary_exc:  # noqa: BLE001 — fallback controlado
        logger.warning(
            "Falló la estrategia '%s': %s",
            getattr(strategy, "name", requested_name),
            primary_exc,
        )
        return _passthrough(
            request,
            warning=(
                f"Real-ESRGAN falló: {primary_exc}. Se devolvió la imagen original."
            ),
        )


def _passthrough(request: UpscaleRequest, *, warning: str) -> UpscaleResult:
    if request.png_bytes is not None and request.image_bgra is not None:
        src_w, src_h = request.image_bgra.shape[1], request.image_bgra.shape[0]
        png_bytes = request.png_bytes
    elif request.image_bgra is not None:
        src_w, src_h = request.image_bgra.shape[1], request.image_bgra.shape[0]
        png_bytes = encode_png_bgra(request.image_bgra)
    elif request.png_bytes is not None:
        png_bytes = request.png_bytes
        src_w, src_h = 0, 0
    else:
        raise UpscaleError(warning)

    return UpscaleResult(
        png_bytes=png_bytes,
        backend="passthrough",
        device="n/a",
        scale_factor=1.0,
        source_size=(src_w, src_h),
        final_size=(src_w, src_h),
        inference_ms=0.0,
        warning=warning,
    )


def _log_result(result: UpscaleResult) -> None:
    logger.info(
        "escalado backend=%s device=%s inference_ms=%.1f "
        "source=%sx%s final=%sx%s factor=%.2f",
        result.backend,
        result.device,
        result.inference_ms,
        result.source_size[0],
        result.source_size[1],
        result.final_size[0],
        result.final_size[1],
        result.scale_factor,
    )
    if result.warning:
        logger.warning("%s", result.warning)


def _find_project_root(start: Path) -> Path | None:
    current = start if start.is_dir() else start.parent
    for _ in range(8):
        if (current / "pyproject.toml").is_file():
            return current
        if current.parent == current:
            break
        current = current.parent
    return None


__all__ = [
    "ScaleOutcome",
    "WARNING_PREFIX",
    "get_scale_defaults",
    "scale_image",
    "UpscaleError",
]
