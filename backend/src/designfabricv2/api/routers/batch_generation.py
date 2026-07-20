"""Endpoint de DesignFabric: job batch de generación IA (N conceptos vía Ollama + N imágenes vía Flux).

Adaptado de `DesignFabric/backend/src/designfabric/api/routers/batch.py`: el
router ya no llama `store.add(job); job_queue.enqueue(job.id)` directamente,
sino `dispatcher.submit(job)` (Fase 4, Feature Registry). El handler que
antes vivía hardcodeado dentro de `GpuJobWorker._process` en el `worker.py`
ORIGINAL de DesignFabric se separa acá como `build_handlers`.
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends

from designfabricv2.api.dependencies import get_job_dispatcher
from designfabricv2.api.dispatcher import JobDispatcher
from designfabricv2.api.schemas import BatchJobRequest, JobCreatedResponse
from designfabricv2.core.config import Settings
from designfabricv2.core.generation.pipeline import run_batch
from designfabricv2.jobs.models import Job, JobType
from designfabricv2.jobs.store import JobStore
from designfabricv2.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["batch"])


@router.post("/batch", response_model=JobCreatedResponse, status_code=202)
def create_batch_job(
    payload: BatchJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job batch: N conceptos vía Ollama + N imágenes vía Flux."""
    job = Job.new(JobType.BATCH, payload)
    dispatcher.submit(job)
    logger.info("Job %s encolado (batch, n=%d, modelo=%s)", job.id, payload.num_images, payload.ollama_model)
    return JobCreatedResponse(job_id=job.id, status=job.status)


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    """Handler de `batch`. Igual que en ClearCut, `JobHandler` no expone el `job_id` al
    handler (jobs/worker.py, Fase 2, cerrado); se usa un uuid propio por job en vez del
    `job_id` que usaba el `worker.py` original de DesignFabric, dentro de una subcarpeta
    fija `batch/` (mismo patrón que las features de ClearCut)."""

    def handle(payload: BatchJobRequest, reporter: WebSocketProgressReporter) -> Any:
        output_dir = f"{settings.output_dir}/batch/{uuid.uuid4().hex}"
        return run_batch(
            payload.num_images,
            ollama_model=payload.ollama_model,
            output_dir=output_dir,
            reporter=reporter,
            ollama_host=settings.ollama_host,
        )

    return {JobType.BATCH: handle}
