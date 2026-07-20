"""Feature Registry: una única fuente de verdad de qué features existen, qué router HTTP
y qué handlers de job aportan, y a qué worker (GPU/CPU) pertenecen.

`app.py` itera `FEATURE_REGISTRY` para montar routers y construir los
diccionarios de handlers de cada worker sin ningún `if/else` hardcodeado por
feature: agregar una feature nueva es agregar una entrada acá.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Literal

from fastapi import APIRouter

from designfabricv2.api.routers import clearcut_batch, remove_background, scale
from designfabricv2.core.config import Settings
from designfabricv2.jobs.models import JobType
from designfabricv2.jobs.store import JobStore
from designfabricv2.jobs.worker import JobHandler

logger = logging.getLogger(__name__)


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
)

LOCAL_AI_AVAILABLE: bool
_gpu_modules: tuple[FeatureModule, ...]
try:
    from designfabricv2.api.routers import batch_generation, single_image

    _gpu_modules = (
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
    LOCAL_AI_AVAILABLE = True
except ImportError as exc:
    logger.warning(
        "Módulo de IA local no disponible (falta instalar el extra 'local-ai'): %s", exc
    )
    _gpu_modules = ()
    LOCAL_AI_AVAILABLE = False

FEATURE_REGISTRY: tuple[FeatureModule, ...] = _cpu_modules + _gpu_modules
