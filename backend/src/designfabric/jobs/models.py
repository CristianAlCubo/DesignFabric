"""Modelo interno de un job (no confundir con los schemas pydantic del API público)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class JobType(str, Enum):
    """Tipo de trabajo encolado para alguno de los workers (GPU o CPU).

    `REMOVE_BACKGROUND`, `SCALE` y `CLEARCUT_BATCH` son placeholders para las
    features de ClearCut que se implementan en una fase posterior — solo se
    declaran los valores del enum acá, sin handlers todavía.
    """

    BATCH = "batch"
    SINGLE_IMAGE = "single_image"
    REMOVE_BACKGROUND = "remove_background"
    SCALE = "scale"
    CLEARCUT_BATCH = "clearcut_batch"
    MULTI_EXPORT = "multi_export"
    CONVERT = "convert"


class JobStatus(str, Enum):
    """Estado del ciclo de vida de un job."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(slots=True)
class Job:
    """Unidad de trabajo encolada para un `JobWorker`.

    `payload` y `result` quedan tipados como `Any`: el worker genérico no
    conoce los tipos concretos de cada feature (eso vive en los schemas
    pydantic y en los handlers registrados por `api/registry.py` en una fase
    posterior).
    """

    id: str
    type: JobType
    payload: Any
    status: JobStatus = JobStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    finished_at: datetime | None = None
    result: Any | None = None
    error: str | None = None
    cancel_requested: bool = False

    @staticmethod
    def new(job_type: JobType, payload: Any) -> Job:
        """Crea un job nuevo en estado QUEUED con un id único."""
        return Job(id=str(uuid.uuid4()), type=job_type, payload=payload)
