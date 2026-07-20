"""Consulta y cancelación de jobs (genérico: no depende de ninguna feature concreta)."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from designfabric.api.dependencies import get_job_store, get_settings_dep
from designfabric.api.schemas import JobStatusResponse
from designfabric.api.serializers import job_to_schema
from designfabric.core.config import Settings
from designfabric.jobs.store import JobStore

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=list[JobStatusResponse])
def list_jobs(
    store: JobStore = Depends(get_job_store),
    settings: Settings = Depends(get_settings_dep),
) -> list[JobStatusResponse]:
    """Lista todos los jobs conocidos, más recientes primero (para reconstruir el historial en la UI)."""
    return [job_to_schema(job, settings) for job in store.list()]


@router.get("/{job_id}", response_model=JobStatusResponse)
def get_job(
    job_id: str,
    store: JobStore = Depends(get_job_store),
    settings: Settings = Depends(get_settings_dep),
) -> JobStatusResponse:
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    return job_to_schema(job, settings)


@router.delete("/{job_id}", status_code=204)
def cancel_job(job_id: str, store: JobStore = Depends(get_job_store)) -> None:
    """Cancela un job solo si todavía está en cola; 409 si ya empezó a correr o ya terminó."""
    job = store.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job no encontrado")
    if not store.mark_cancelled(job_id):
        raise HTTPException(status_code=409, detail="El job ya está en ejecución o finalizado")
    logger.info("Job %s cancelado", job_id)
