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
from designfabric.core.imaging.silhouette_strategies import create_silhouette_strategy
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clearcut", tags=["clearcut-remove-background"])

# Metadata de las estrategias de silueta para exponer vía GET /api/clearcut/strategies.
# `core/imaging/silhouette_strategies.py` no trae esta metadata (a diferencia de
# `upscale_strategies.SCALE_STRATEGY_META`) — el bridge TS original de ClearCut la
# duplicaba a mano; para esta fusión se genera una sola vez acá y el frontend (Fase
# 5/6) la consume desde este endpoint en vez de volver a duplicarla en TS.
STRATEGY_META: tuple[dict[str, str], ...] = (
    {"id": "white_background", "label": "Fondo blanco", "description": "Rápida: ideal para fondos blancos limpios."},
    {
        "id": "color_background",
        "label": "Fondo de color",
        "description": "Robusta: detecta el color predominante en las esquinas.",
    },
)


@router.get("/strategies")
def list_strategies() -> list[dict[str, str]]:
    """Fuente de verdad de las estrategias de silueta disponibles (para poblar la UI)."""
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
    """Handler de `remove_background`: no recibe el `job_id` (ver `jobs/worker.py`, Fase 2,
    cerrado), así que el nombre de salida se genera acá con un uuid propio, dentro de una
    subcarpeta fija por feature (mismo patrón para scale/clearcut-batch)."""

    def handle(payload: RemoveBackgroundJobRequest, reporter: WebSocketProgressReporter) -> dict:
        strategy = create_silhouette_strategy(payload.strategy)
        output_dir = Path(settings.output_dir) / "remove-background"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uuid.uuid4().hex}.png"

        # `process_image` devuelve un np.ndarray (no serializable a JSON): el handler
        # solo propaga las rutas, que es lo único que `job_to_schema` necesita.
        process_image(Path(payload.input_path), output_path, strategy)
        return {"output_path": str(output_path)}

    return {JobType.REMOVE_BACKGROUND: handle}
