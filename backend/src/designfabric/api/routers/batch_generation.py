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

from fastapi import APIRouter, Depends, HTTPException

from designfabric.api.dependencies import get_job_dispatcher
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.local_ai import LOCAL_AI_AVAILABLE
from designfabric.api.schemas import BatchJobRequest, JobCreatedResponse
from designfabric.core.config import Settings
from designfabric.core.generation.pipeline import run_batch
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["batch"])


def _require_local_ai_if_needed(payload: BatchJobRequest) -> None:
    needs_local_ai = payload.llm_provider == "ollama" or payload.image_provider == "flux"
    if needs_local_ai and not LOCAL_AI_AVAILABLE:
        raise HTTPException(
            status_code=503,
            detail=(
                "Los providers ollama/flux requieren el extra 'local-ai'. "
                "Usa llm_provider=test e image_provider=test, o instala local-ai."
            ),
        )


@router.post("/batch", response_model=JobCreatedResponse, status_code=202)
def create_batch_job(
    payload: BatchJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job batch: N conceptos vía LLM provider + N imágenes vía image provider."""
    _require_local_ai_if_needed(payload)
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
            llm_provider=payload.llm_provider,
            image_provider=payload.image_provider,
        )

    return {JobType.BATCH: handle}
