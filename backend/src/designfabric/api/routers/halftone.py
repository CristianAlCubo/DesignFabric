"""Endpoint de Utilidades: conversión a semitonos (halftone) de una única imagen.

El export full-res corre como job asíncrono con afinidad de CPU (patrón `convert`/
`scale`). La previsualización es un endpoint **síncrono** de baja resolución que
responde directo (sin cola), pensado para iterar en vivo sobre los parámetros.
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
    HalftonePreviewRequest,
    HalftonePreviewResponse,
    JobCreatedResponse,
)
from designfabric.core.config import Settings
from designfabric.core.imaging.halftone_pipeline import (
    make_halftone_preview,
    make_halftone_single,
)
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/utilities", tags=["utilities-halftone"])


@router.post("/halftone", response_model=JobCreatedResponse, status_code=202)
def create_halftone_job(
    payload: HalftoneJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job de export halftone full-res para una única imagen."""
    job = Job.new(JobType.HALFTONE, payload)
    dispatcher.submit(job)
    logger.info("Job %s encolado (halftone, method=%s)", job.id, payload.halftone_method)
    return JobCreatedResponse(job_id=job.id, status=job.status)


@router.post("/halftone/preview", response_model=HalftonePreviewResponse)
def halftone_preview(payload: HalftonePreviewRequest) -> HalftonePreviewResponse:
    """Genera una previsualización a baja resolución (síncrona, sin cola).

    Devuelve la imagen como data URL PNG para que el frontend la muestre directo,
    igual que `getImagePreview`.
    """
    with Image.open(payload.input_path) as img:
        img.load()
        preview = make_halftone_preview(
            img,
            preview_max_side=payload.preview_max_side,
            crop_black_background=payload.crop_black_background,
            crop_black_threshold=payload.crop_black_threshold,
            black_point=payload.black_point,
            white_point=payload.white_point,
            gamma=payload.gamma,
            invert_for_dark_shirt=payload.invert_for_dark_shirt,
            halftone_method=payload.halftone_method,
            screen_frequency=payload.screen_frequency,
            screen_angle=payload.screen_angle,
            dot_shape=payload.dot_shape,
        )

    buffer = BytesIO()
    preview.save(buffer, format="PNG")
    encoded = base64.b64encode(buffer.getvalue()).decode("ascii")
    return HalftonePreviewResponse(
        image_data_url=f"data:image/png;base64,{encoded}",
        width=preview.width,
        height=preview.height,
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
            out_img = make_halftone_single(
                img,
                crop_black_background=payload.crop_black_background,
                crop_black_threshold=payload.crop_black_threshold,
                black_point=payload.black_point,
                white_point=payload.white_point,
                gamma=payload.gamma,
                invert_for_dark_shirt=payload.invert_for_dark_shirt,
                halftone_method=payload.halftone_method,
                screen_frequency=payload.screen_frequency,
                screen_angle=payload.screen_angle,
                dot_shape=payload.dot_shape,
            )
        # PNG lossless conservando alpha; se preserva el DPI seteado por el core.
        out_img.save(output_path, format="PNG", dpi=out_img.info.get("dpi"))
        return {"output_path": str(output_path)}

    return {JobType.HALFTONE: handle}
