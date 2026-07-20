"""Endpoint de ClearCut: procesamiento por lotes (recorte + escalado)."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from designfabric.api.dependencies import get_job_dispatcher
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.schemas import ClearcutBatchJobRequest, JobCreatedResponse
from designfabric.core.config import Settings
from designfabric.core.imaging.background_remover import RemovalConfig
from designfabric.core.imaging.batch.input_sources import create_input_source
from designfabric.core.imaging.batch.output_targets import create_output_target
from designfabric.core.imaging.batch.processor import run_batch
from designfabric.core.imaging.batch.types import BatchConfig
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clearcut", tags=["clearcut-batch"])


@router.post("/batch", response_model=JobCreatedResponse, status_code=202)
def create_clearcut_batch_job(
    payload: ClearcutBatchJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job de batch de ClearCut (recorte + escalado sobre una carpeta o lista de archivos)."""
    job = Job.new(JobType.CLEARCUT_BATCH, payload)
    dispatcher.submit(job)
    logger.info("Job %s encolado (clearcut-batch, kind=%s)", job.id, payload.input.kind)
    return JobCreatedResponse(job_id=job.id, status=job.status)


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    """Handler de `clearcut_batch`.

    A diferencia de `remove_background`/`scale`, este batch SÍ escribe directo a la
    carpeta que el usuario eligió (`payload.output_dir`), no a `settings.output_dir` —
    es intencional, coincide con el comportamiento original de ClearCut standalone.

    Limitación conocida: cancelar un batch a medio proceso queda fuera de alcance de
    esta fase. `JobHandler` (jobs/worker.py, Fase 2, cerrado) no le pasa el `job_id` al
    handler, así que no hay forma de que este closure consulte
    `store.get(job_id).status` para armar un `should_cancel` cooperativo sin tocar el
    worker genérico. Por eso se pasa `should_cancel=None`: `DELETE /api/jobs/{id}`
    sigue funcionando igual que hoy (solo cancela jobs todavía en QUEUED, antes de que
    el worker los tome). El CLI standalone conserva su propio mecanismo de cancelación
    por SIGTERM, que no se toca.
    """

    def handle(payload: ClearcutBatchJobRequest, reporter: WebSocketProgressReporter) -> dict:
        config = BatchConfig(
            removal_strategy=payload.removal_strategy,
            scale_strategy=payload.scale_strategy,
            scale_factor=payload.factor,
            removal=RemovalConfig(),
        )

        if payload.input.kind == "folder":
            source = create_input_source("folder", directory=Path(payload.input.directory or ""))
        else:
            source = create_input_source("files", paths=[Path(p) for p in payload.input.paths or []])

        target = create_output_target("directory", directory=Path(payload.output_dir))

        report = run_batch(config, source, target, reporter=reporter, should_cancel=None)
        return report.to_dict()

    return {JobType.CLEARCUT_BATCH: handle}
