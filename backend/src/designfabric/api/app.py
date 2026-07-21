"""Application factory de FastAPI: arma el estado compartido y monta los routers.

Se ejecuta con `uvicorn designfabric.api.app:app` (ver README/CLAUDE.md
para el comando exacto usado en desarrollo).

Itera `FEATURE_REGISTRY` (ver `api/registry.py`) para montar routers Y
construir los diccionarios de handlers de cada worker (GPU/CPU): agregar una
feature nueva no requiere tocar este archivo.
"""

from __future__ import annotations

import asyncio
import logging
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from designfabric.api.dispatcher import JobDispatcher
from designfabric.api.registry import FEATURE_REGISTRY
from designfabric.api.routers import features as features_router
from designfabric.api.routers import generation_providers as generation_providers_router
from designfabric.api.routers import health as health_router
from designfabric.api.routers import jobs as jobs_router
from designfabric.api.routers import model_path_settings as model_path_settings_router
from designfabric.api.routers import openrouter_settings as openrouter_settings_router
from designfabric.api.routers import progress_ws as progress_ws_router
from designfabric.core.config import get_settings
from designfabric.core.generation.openrouter.runtime_config import get_openrouter_runtime
from designfabric.core.imaging.model_path_runtime import get_model_path_runtime
from designfabric.jobs.models import JobType
from designfabric.jobs.queue import JobQueue
from designfabric.jobs.store import JobStore
from designfabric.jobs.worker import CpuJobWorker, GpuJobWorker, JobHandler
from designfabric.jobs.ws_reporter import ProgressHub


def _configure_logging() -> None:
    """Logging a stdout con formato legible y timestamp.

    La app de escritorio (Electron) captura el stdout del proceso backend y
    lo muestra en su consola de observabilidad — este formato es lo que
    termina viéndose ahí, además de en la terminal en desarrollo.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def create_app() -> FastAPI:
    """Construye la app de FastAPI con sus dependencias (store/colas/hub/workers) inyectadas en `app.state`."""
    _configure_logging()
    settings = get_settings()
    get_openrouter_runtime().seed_from_settings(settings)
    get_model_path_runtime().seed_from_settings(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Los workers se arrancan ligados al event loop de FastAPI: lo necesitan
        # para publicar eventos de progreso desde sus propios hilos (ver ws_reporter.py).
        loop = asyncio.get_running_loop()
        app.state.gpu_worker.start(loop)
        app.state.cpu_worker.start(loop)
        yield

    app = FastAPI(title="DesignFabric API", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        # El backend solo escucha en localhost y lo consume la app de escritorio: no hay
        # superficie de ataque cross-origin real que justifique restringir el origen aquí.
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = JobStore()
    gpu_queue, cpu_queue = JobQueue(), JobQueue()
    hub = ProgressHub()

    affinity_by_type: dict[JobType, str] = {
        jt: module.worker_affinity for module in FEATURE_REGISTRY for jt in module.job_types
    }
    dispatcher = JobDispatcher(store, gpu_queue, cpu_queue, affinity_by_type)

    gpu_handlers: dict[JobType, JobHandler] = {}
    cpu_handlers: dict[JobType, JobHandler] = {}
    for module in FEATURE_REGISTRY:
        handlers = module.build_handlers(settings, store)
        target = gpu_handlers if module.worker_affinity == "gpu" else cpu_handlers
        target.update(handlers)
        app.include_router(module.router)

    app.state.settings = settings
    app.state.job_store = store
    app.state.job_dispatcher = dispatcher
    app.state.progress_hub = hub
    app.state.gpu_worker = GpuJobWorker(store, gpu_queue, hub, gpu_handlers)
    app.state.cpu_worker = CpuJobWorker(store, cpu_queue, hub, cpu_handlers)

    os.makedirs(settings.output_dir, exist_ok=True)
    app.mount("/output", StaticFiles(directory=settings.output_dir), name="output")

    app.include_router(jobs_router.router)
    app.include_router(progress_ws_router.router)
    app.include_router(health_router.router)
    app.include_router(features_router.router)
    app.include_router(generation_providers_router.router)
    app.include_router(openrouter_settings_router.router)
    app.include_router(model_path_settings_router.router)

    return app


app = create_app()
