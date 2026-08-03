"""Endpoint de Utilidades: conversión de formato de imágenes (individual y lote → zip)."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from designfabric.api.dependencies import get_job_dispatcher
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.schemas import (
    ConvertBatchJobRequest,
    ConvertJobRequest,
    JobCreatedResponse,
)
from designfabric.core.config import Settings
from designfabric.core.imaging.convert_pipeline import (
    convert_batch,
    convert_one,
    resolve_target_format,
)
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/utilities", tags=["utilities-convert"])

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


@router.post("/convert", response_model=JobCreatedResponse, status_code=202)
def create_convert_job(
    payload: ConvertJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job de conversión de una única imagen."""
    job = Job.new(JobType.CONVERT, payload)
    dispatcher.submit(job)
    logger.info("Job %s encolado (convert, target=%s)", job.id, payload.target_format)
    return JobCreatedResponse(job_id=job.id, status=job.status)


@router.post("/convert-batch", response_model=JobCreatedResponse, status_code=202)
def create_convert_batch_job(
    payload: ConvertBatchJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job de conversión en lote (N imágenes → un `.zip`)."""
    job = Job.new(JobType.CONVERT, payload)
    dispatcher.submit(job)
    logger.info(
        "Job %s encolado (convert-batch, target=%s, images=%d)",
        job.id,
        payload.target_format,
        len(payload.image_paths),
    )
    return JobCreatedResponse(job_id=job.id, status=job.status)


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    """Handler de `convert`: un mismo `JobType` sirve el modo individual y el de lote,
    distinguidos por el tipo del payload (mismo patrón CPU-affinity que `scale`/`multi_export`)."""

    output_dir = Path(settings.output_dir) / "convert"

    def handle_single(payload: ConvertJobRequest) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        spec = resolve_target_format(payload.target_format)
        output_path = output_dir / f"{uuid.uuid4().hex}{spec.extension}"
        convert_one(
            Path(payload.input_path),
            output_path,
            payload.target_format,
            quality=payload.quality,
            webp_lossless=payload.webp_lossless,
        )
        return {"output_path": str(output_path)}

    def handle_batch(payload: ConvertBatchJobRequest, reporter: WebSocketProgressReporter) -> dict:
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = _SAFE_NAME.sub("_", payload.output_name).strip("_") if payload.output_name else ""
        zip_path = output_dir / f"{stem or 'convert'}-{uuid.uuid4().hex}.zip"
        report = convert_batch(
            [Path(p) for p in payload.image_paths],
            payload.target_format,
            zip_path,
            quality=payload.quality,
            webp_lossless=payload.webp_lossless,
            reporter=reporter,
        )
        return report.to_dict()

    def handle(payload: Any, reporter: WebSocketProgressReporter) -> dict:
        if isinstance(payload, ConvertBatchJobRequest):
            return handle_batch(payload, reporter)
        return handle_single(payload)

    return {JobType.CONVERT: handle}
