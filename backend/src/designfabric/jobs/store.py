"""Repositorio en memoria de jobs.

Sin base de datos: es un solo proceso local de escritorio, el historial de
jobs no necesita sobrevivir a un reinicio del backend. Protegido con un lock
porque se accede tanto desde el event loop de FastAPI (requests HTTP) como
desde los hilos de los workers (GPU y CPU).
"""

from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Any

from designfabric.jobs.models import Job, JobStatus


class JobStore:
    """Repositorio en memoria de `Job`, con transiciones de estado atómicas.

    `result` se tipa como `Any | None` porque el store guarda resultados
    heterogéneos de features distintas (generación IA, ClearCut, etc.) — no
    le corresponde importar tipos concretos de ninguna feature.
    """

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}
        self._lock = threading.Lock()

    def add(self, job: Job) -> None:
        with self._lock:
            self._jobs[job.id] = job

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            return self._jobs.get(job_id)

    def list(self) -> list[Job]:
        """Devuelve todos los jobs, más recientes primero."""
        with self._lock:
            return sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)

    def mark_running(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)

    def mark_succeeded(self, job_id: str, result: Any) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.SUCCEEDED
            job.result = result
            job.finished_at = datetime.now(timezone.utc)

    def mark_failed(self, job_id: str, error: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.FAILED
            job.error = error
            job.finished_at = datetime.now(timezone.utc)

    def mark_cancelled(self, job_id: str) -> bool:
        """Cancela el job solo si sigue en QUEUED. Devuelve True si se canceló."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None or job.status is not JobStatus.QUEUED:
                return False
            job.status = JobStatus.CANCELLED
            job.cancel_requested = True
            job.finished_at = datetime.now(timezone.utc)
            return True

    def request_cancel(self, job_id: str) -> bool:
        """Solicita cancelación: QUEUED → CANCELLED; RUNNING → flag cooperativa.

        Devuelve False si el job no existe o ya terminó.
        """
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            if job.status is JobStatus.QUEUED:
                job.status = JobStatus.CANCELLED
                job.cancel_requested = True
                job.finished_at = datetime.now(timezone.utc)
                return True
            if job.status is JobStatus.RUNNING:
                job.cancel_requested = True
                return True
            return False

    def is_cancel_requested(self, job_id: str) -> bool:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return False
            return job.cancel_requested or job.status is JobStatus.CANCELLED

    def mark_cancelled_running(self, job_id: str, result: Any | None = None) -> None:
        """Marca un job RUNNING como CANCELLED (salida cooperativa del handler)."""
        with self._lock:
            job = self._jobs[job_id]
            job.status = JobStatus.CANCELLED
            job.cancel_requested = True
            job.result = result
            job.finished_at = datetime.now(timezone.utc)
