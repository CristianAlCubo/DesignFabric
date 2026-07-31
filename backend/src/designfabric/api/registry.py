"""Feature Registry: una única fuente de verdad de qué features existen, qué router HTTP
y qué handlers de job aportan, y a qué worker (GPU/CPU) pertenecen.

`app.py` itera `FEATURE_REGISTRY` para montar routers y construir los
diccionarios de handlers de cada worker sin ningún `if/else` hardcodeado por
feature: agregar una feature nueva es agregar una entrada acá.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Literal

from fastapi import APIRouter

from designfabric.api.local_ai import LOCAL_AI_AVAILABLE
from designfabric.api.routers import (
    batch_generation,
    clearcut_batch,
    multi_export,
    remove_background,
    scale,
    single_image,
)
from designfabric.core.config import Settings
from designfabric.jobs.models import JobType
from designfabric.jobs.store import JobStore
from designfabric.jobs.worker import JobHandler

# Re-export para callers que importaban desde registry.
__all__ = ["FEATURE_REGISTRY", "FeatureModule", "LOCAL_AI_AVAILABLE"]


@dataclass(frozen=True)
class FeatureModule:
    """Una tool/tab autocontenida: su router HTTP + los handlers de job que aporta."""

    name: str
    router: APIRouter
    job_types: tuple[JobType, ...]
    worker_affinity: Literal["gpu", "cpu"]
    build_handlers: Callable[[Settings, JobStore], dict[JobType, JobHandler]]


_cpu_modules: tuple[FeatureModule, ...] = (
    FeatureModule(
        "remove-background",
        remove_background.router,
        (JobType.REMOVE_BACKGROUND,),
        "cpu",
        remove_background.build_handlers,
    ),
    FeatureModule("scale", scale.router, (JobType.SCALE,), "cpu", scale.build_handlers),
    FeatureModule(
        "clearcut-batch",
        clearcut_batch.router,
        (JobType.CLEARCUT_BATCH,),
        "cpu",
        clearcut_batch.build_handlers,
    ),
    FeatureModule(
        "multi-export",
        multi_export.router,
        (JobType.MULTI_EXPORT,),
        "cpu",
        multi_export.build_handlers,
    ),
)

_gpu_modules: tuple[FeatureModule, ...] = (
    FeatureModule(
        "designfabric-batch",
        batch_generation.router,
        (JobType.BATCH,),
        "gpu",
        batch_generation.build_handlers,
    ),
    FeatureModule(
        "designfabric-single",
        single_image.router,
        (JobType.SINGLE_IMAGE,),
        "gpu",
        single_image.build_handlers,
    ),
)

FEATURE_REGISTRY: tuple[FeatureModule, ...] = _cpu_modules + _gpu_modules
