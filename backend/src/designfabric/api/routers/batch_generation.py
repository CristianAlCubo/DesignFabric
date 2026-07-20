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

from designfabric.api.dependencies import get_job_dispatcher
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.generation_guards import require_generation_ready
from designfabric.api.schemas import BatchJobRequest, JobCreatedResponse
from designfabric.core.config import Settings
from designfabric.core.generation.pipeline import run_batch
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["batch"])


@router.post("/batch", response_model=JobCreatedResponse, status_code=202)
def create_batch_job(
    payload: BatchJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job batch: N conceptos vía LLM provider + N imágenes vía image provider."""
    require_generation_ready(
        llm_provider=payload.llm_provider,
        image_provider=payload.image_provider,
        ollama_model=payload.ollama_model,
    )
    job = Job.new(JobType.BATCH, payload)
    dispatcher.submit(job)
    logger.info(
        "Job %s encolado (batch, n=%d, llm=%s, image=%s, modelo=%s)",
        job.id,
        payload.num_images,
        payload.llm_provider,
        payload.image_provider,
        payload.ollama_model,
    )
    return JobCreatedResponse(job_id=job.id, status=job.status)


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    """Handler de `batch`. Cancela de forma cooperativa vía `store.is_cancel_requested`."""

    def handle(payload: BatchJobRequest, reporter: WebSocketProgressReporter) -> Any:
        output_dir = f"{settings.output_dir}/batch/{uuid.uuid4().hex}"
        return run_batch(
            payload.num_images,
            ollama_model=payload.ollama_model,
            output_dir=output_dir,
            reporter=reporter,
            ollama_host=settings.ollama_host,
            llm_provider=payload.llm_provider,
            image_provider=payload.image_provider,
            transparent_background=payload.transparent_background,
            should_cancel=lambda: store.is_cancel_requested(reporter.job_id),
        )

    return {JobType.BATCH: handle}
