"""Endpoint de Utilidades: conversión a semitonos (halftone) de una única imagen.

El export full-res corre como job asíncrono con afinidad de CPU (patrón `convert`/
`scale`). La previsualización es un endpoint **síncrono** de baja resolución que
responde directo (sin cola), pensado para iterar en vivo sobre los parámetros.

Ambos resuelven los parámetros igual (`_analyze`): en modo `quick` el resultado es
determinista, así que el export coincide con lo que mostró el preview.
"""

from __future__ import annotations

import base64
import logging
import uuid
from io import BytesIO
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends
from PIL import Image

from designfabric.api.dependencies import get_job_dispatcher
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.schemas import (
    HalftoneJobRequest,
    HalftoneParams,
    HalftonePreviewRequest,
    HalftonePreviewResponse,
    HalftoneResolvedParams,
    JobCreatedResponse,
)
from designfabric.core.config import Settings
from designfabric.core.imaging.halftone_modes import (
    HalftoneAnalysis,
    HalftoneSettings,
    analyze_halftone,
    render_halftone,
    render_halftone_preview,
    resolve_quick_halftone,
)
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/utilities", tags=["utilities-halftone"])


def _analyze(image: Image.Image, payload: HalftoneParams) -> HalftoneAnalysis:
    """Resuelve los parámetros del render según el modo pedido."""
    if payload.mode == "quick":
        return resolve_quick_halftone(
            image,
            garment=payload.garment,
            background=payload.background,
            background_threshold=payload.background_threshold,
        )
    return analyze_halftone(
        image,
        HalftoneSettings(
            garment=payload.garment,
            background=payload.background,
            background_threshold=payload.background_threshold,
            black_point=payload.black_point,
            white_point=payload.white_point,
            gamma=payload.gamma,
            halftone_method=payload.halftone_method,
            screen_frequency=payload.screen_frequency,
            screen_angle=payload.screen_angle,
            dot_shape=payload.dot_shape,
            min_dot_tone=payload.min_dot_tone,
        ),
    )


@router.post("/halftone", response_model=JobCreatedResponse, status_code=202)
def create_halftone_job(
    payload: HalftoneJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job de export halftone full-res para una única imagen."""
    job = Job.new(JobType.HALFTONE, payload)
    dispatcher.submit(job)
    logger.info("Job %s encolado (halftone, mode=%s)", job.id, payload.mode)
    return JobCreatedResponse(job_id=job.id, status=job.status)


@router.post("/halftone/preview", response_model=HalftonePreviewResponse)
def halftone_preview(payload: HalftonePreviewRequest) -> HalftonePreviewResponse:
    """Genera una previsualización a baja resolución (síncrona, sin cola).

    Devuelve la imagen como data URL PNG (igual que `getImagePreview`) junto con los
    parámetros resueltos y los avisos de imprimibilidad.
    """
    with Image.open(payload.input_path) as img:
        img.load()
        analysis = _analyze(img, payload)
        preview = render_halftone_preview(
            img, analysis.settings, preview_max_side=payload.preview_max_side
        )

    buffer = BytesIO()
    preview.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    resolved = analysis.settings
    return HalftonePreviewResponse(
        image_data_url=f"data:image/png;base64,{encoded}",
        width=preview.width,
        height=preview.height,
        resolved=HalftoneResolvedParams(
            garment=resolved.garment,
            background=analysis.background,
            background_threshold=resolved.background_threshold,
            black_point=resolved.black_point,
            white_point=resolved.white_point,
            gamma=resolved.gamma,
            halftone_method=resolved.halftone_method,
            screen_frequency=resolved.screen_frequency,
            screen_angle=resolved.screen_angle,
            dot_shape=resolved.dot_shape,
            min_dot_tone=resolved.min_dot_tone,
        ),
        output_width=analysis.output_size[0],
        output_height=analysis.output_size[1],
        small_dot_ratio=analysis.small_dot_ratio,
        warnings=list(analysis.warnings),
    )


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    """Handler de `halftone`: escribe un PNG RGBA transparente en `output/halftone`
    (mismo patrón CPU-affinity y uuid propio que `scale`/`convert`)."""

    output_dir = Path(settings.output_dir) / "halftone"

    def handle(payload: HalftoneJobRequest, reporter: WebSocketProgressReporter) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uuid.uuid4().hex}.png"

        with Image.open(payload.input_path) as img:
            img.load()
            out_img = render_halftone(img, _analyze(img, payload).settings)
        # PNG lossless conservando alpha; se preserva el DPI seteado por el core.
        out_img.save(output_path, format="PNG", dpi=out_img.info.get("dpi"))
        return {"output_path": str(output_path)}

    return {JobType.HALFTONE: handle}
