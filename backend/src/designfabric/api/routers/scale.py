"""Endpoint de ClearCut: escalado (vectorial o Real-ESRGAN) de una única imagen."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends

from designfabric.api.dependencies import get_job_dispatcher
from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.schemas import JobCreatedResponse, ScaleJobRequest
from designfabric.core.config import Settings
from designfabric.core.imaging.model_assets import ensure_models
from designfabric.core.imaging.upscale_pipeline import get_scale_defaults, scale_image
from designfabric.core.imaging.vector_engine import ExportConfig, TraceConfig
from designfabric.jobs.models import Job, JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import WebSocketProgressReporter

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/clearcut", tags=["clearcut-scale"])


@router.get("/scale/defaults")
def scale_defaults() -> dict:
    """Defaults de trace/export/estrategias/config para hidratar la UI (Fase 5/6)."""
    return get_scale_defaults()


@router.post("/scale/ensure-models")
def ensure_scale_models() -> dict:
    """Prepara (descarga si falta) los modelos IA de escalado, equivalente al `ensureModels`
    que Electron llamaba al arrancar. `ensure_models()` es la función de alto nivel que ya
    existe en `model_assets.py` para "preparar todos los modelos conocidos"."""
    return ensure_models().to_dict()


@router.post("/scale", response_model=JobCreatedResponse, status_code=202)
def create_scale_job(
    payload: ScaleJobRequest,
    dispatcher: JobDispatcher = Depends(get_job_dispatcher),
) -> JobCreatedResponse:
    """Encola un job de escalado para una única imagen."""
    job = Job.new(JobType.SCALE, payload)
    dispatcher.submit(job)
    logger.info("Job %s encolado (scale, strategy=%s)", job.id, payload.strategy)
    return JobCreatedResponse(job_id=job.id, status=job.status)


def build_handlers(settings: Settings, store: JobStore) -> dict[JobType, Any]:
    """Handler de `scale`: mismo patrón que `remove_background` (sin `job_id`, uuid propio
    dentro de una subcarpeta fija `scale/`)."""

    def handle(payload: ScaleJobRequest, reporter: WebSocketProgressReporter) -> dict:
        output_dir = Path(settings.output_dir) / "scale"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{uuid.uuid4().hex}.png"

        trace = TraceConfig(**payload.trace.model_dump()) if payload.trace is not None else None

        export_kwargs: dict[str, Any] = {}
        if payload.width is not None:
            export_kwargs["width_px"] = payload.width
        if payload.height is not None:
            export_kwargs["height_px"] = payload.height
        if payload.dpi is not None:
            export_kwargs["dpi"] = payload.dpi
        export = ExportConfig(**export_kwargs) if export_kwargs else None

        outcome = scale_image(
            Path(payload.input_path),
            output_path,
            strategy=payload.strategy,
            trace=trace,
            export=export,
        )
        result = outcome.result
        return {
            "output_path": str(outcome.output_path),
            "backend": result.backend,
            "device": result.device,
            "scale_factor": result.scale_factor,
            "source_size": result.source_size,
            "final_size": result.final_size,
            "inference_ms": result.inference_ms,
            "warning": result.warning,
        }

    return {JobType.SCALE: handle}
