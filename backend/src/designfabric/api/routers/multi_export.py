"""Endpoint de ClearCut: exportación multi-tamaño (N imágenes × M tamaños → un `.zip`)."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from designfabric.api.dependencies import get_job_dispatcher
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.schemas import JobCreatedResponse, MultiExportJobRequest
from designfabric.core.config import Settings
from designfabric.core.imaging.multi_export_pipeline import SizeRow, run_multi_export
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clearcut", tags=["clearcut-multi-export"])

_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


@router.post("/multi-export", response_model=JobCreatedResponse, status_code=202)
def create_multi_export_job(
    payload: MultiExportJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job de exportación multi-tamaño."""
    job = Job.new(JobType.MULTI_EXPORT, payload)
    dispatcher.submit(job)
    logger.info(
        "Job %s encolado (multi-export, images=%d, sizes=%d)",
        job.id,
        len(payload.image_paths),
        len(payload.sizes),
    )
    return JobCreatedResponse(job_id=job.id, status=job.status)


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    """Handler de `multi_export`: mismo patrón CPU-affinity que `scale`/`clearcut_batch`."""

    def handle(payload: MultiExportJobRequest, reporter: WebSocketProgressReporter) -> dict:
        output_dir = Path(settings.output_dir) / "multi-export"
        output_dir.mkdir(parents=True, exist_ok=True)
        stem = _SAFE_NAME.sub("_", payload.output_name).strip("_") if payload.output_name else "export"
        zip_path = output_dir / f"{stem or 'export'}-{uuid.uuid4().hex}.zip"

        sizes = [
            SizeRow(
                label=row.label,
                mode=row.mode,
                prefix=row.prefix,
                width=row.width,
                height=row.height,
                percent=row.percent,
                template=row.template,
            )
            for row in payload.sizes
        ]
        image_paths = [Path(p) for p in payload.image_paths]

        report = run_multi_export(image_paths, sizes, zip_path, reporter=reporter)
        return report.to_dict()

    return {JobType.MULTI_EXPORT: handle}
