"""Endpoint de ClearCut: eliminación de fondo de una única imagen (rápido, sin progreso incremental)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from designfabric.api.dependencies import get_job_dispatcher
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.schemas import JobCreatedResponse, RemoveBackgroundJobRequest
from designfabric.core.config import Settings
from designfabric.core.imaging.background_remover import process_image
from designfabric.core.imaging.background_removal_strategies import create_background_removal_strategy
from designfabric.core.imaging.model_path_runtime import get_model_path_runtime
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clearcut", tags=["clearcut-remove-background"])

STRATEGY_META: tuple[dict[str, str], ...] = (
    {
        "id": "white_background",
        "label": "Fondo blanco",
        "description": "Rápida: ideal para fondos blancos limpios.",
    },
    {
        "id": "color_background",
        "label": "Fondo de color",
        "description": "Robusta: detecta el color predominante en las esquinas.",
    },
    {
        "id": "sam2_vitmatte",
        "label": "SAM2 + ViTMatte",
        "description": "IA local: SAM2 Tiny + ViTMatte con alpha suave (requiere modelos en Ajustes).",
    },
    {
        "id": "isnet_general",
        "label": "IA local (general)",
        "description": (
            "IS-Net general-use: segmentación de un solo paso, bordes duros y consistentes "
            "— recomendada para ilustraciones (requiere modelo en Ajustes)."
        ),
    },
    {
        "id": "rembg_illustration",
        "label": "rembg (ilustraciones/anime)",
        "description": (
            "IS-Net-anime vía rembg: entrenado específicamente en arte anime/2D. Descarga el "
            "modelo (~170MB) automáticamente en el primer uso (requiere internet esa vez)."
        ),
    },
    {
        "id": "birefnet_sam2_matte",
        "label": "BiRefNet + SAM2 + Matte",
        "description": (
            "BiRefNet (principal, vía rembg) + SAM2 (refinamiento opcional, si está "
            "configurado en Ajustes) + ViTMatte o BRIA RMBG (automático según lo "
            "configurado). Descarga ~1GB de modelos en el primer uso (requiere internet esa "
            "vez) y, sin ViTMatte configurado, corre dos redes de ~1GB por imagen en CPU "
            "(varias veces más lenta que las demás estrategias)."
        ),
    },
)


@router.get("/strategies")
def list_strategies() -> list[dict[str, str]]:
    """Fuente de verdad de las estrategias de eliminación de fondo disponibles."""
    return list(STRATEGY_META)


@router.post("/remove-background", response_model=JobCreatedResponse, status_code=202)
def create_remove_background_job(
    payload: RemoveBackgroundJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job de eliminación de fondo para una única imagen."""
    job = Job.new(JobType.REMOVE_BACKGROUND, payload)
    dispatcher.submit(job)
    logger.info("Job %s encolado (remove-background, strategy=%s)", job.id, payload.strategy)
    return JobCreatedResponse(job_id=job.id, status=job.status)


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    """Handler de `remove_background`."""

    def handle(payload: RemoveBackgroundJobRequest, reporter: WebSocketProgressReporter) -> dict:
        del reporter
        runtime = get_model_path_runtime()
        runtime.seed_from_settings(settings)
        strategy = create_background_removal_strategy(
            payload.strategy,
            model_paths=runtime.resolve_paths(),
        )
        output_dir = Path(settings.output_dir) / "remove-background"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uuid.uuid4().hex}.png"

        process_image(Path(payload.input_path), output_path, strategy)
        return {"output_path": str(output_path)}

    return {JobType.REMOVE_BACKGROUND: handle}
