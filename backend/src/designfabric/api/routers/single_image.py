"""Endpoint de DesignFabric: generación de una única imagen a partir de un prompt libre.

Ver `batch_generation.py` para la explicación del patrón (dispatcher +
build_handlers + subcarpeta con uuid propio en vez de `job_id`).
"""

from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, Depends

from designfabric.api.dependencies import get_job_dispatcher
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.generation_guards import require_generation_ready
from designfabric.api.schemas import JobCreatedResponse, SingleImageJobRequest
from designfabric.core.config import Settings
from designfabric.core.generation.pipeline import run_single_image
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["single-image"])


@router.post("/single-image", response_model=JobCreatedResponse, status_code=202)
def create_single_image_job(
    payload: SingleImageJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job de imagen única: bypasea el LLM y usa el image provider elegido."""
    require_generation_ready(image_provider=payload.image_provider)
    job = Job.new(JobType.SINGLE_IMAGE, payload)
    dispatcher.submit(job)
    logger.info(
        "Job %s encolado (single-image, image=%s, prompt=%r)",
        job.id,
        payload.image_provider,
        payload.prompt[:60],
    )
    return JobCreatedResponse(job_id=job.id, status=job.status)


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    def handle(payload: SingleImageJobRequest, reporter: WebSocketProgressReporter) -> Any:
        output_dir = f"{settings.output_dir}/single-image/{uuid.uuid4().hex}"
        return run_single_image(
            payload.prompt,
            apply_style=payload.apply_style_suffix,
            output_dir=output_dir,
            reporter=reporter,
            image_provider=payload.image_provider,
        )

    return {JobType.SINGLE_IMAGE: handle}
