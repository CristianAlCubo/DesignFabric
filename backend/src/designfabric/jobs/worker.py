"""Workers de jobs: consumen una `JobQueue` y ejecutan cada job con el handler
registrado para su tipo.

Dos políticas de concurrencia, según el recurso que cada tipo de job
consume:

- `GpuJobWorker`: un solo hilo daemon. Ollama y FLUX.2 comparten la misma
  VRAM y no pueden correr en paralelo, así que garantiza que nunca haya más
  de un job de GPU corriendo a la vez.
- `CpuJobWorker`: un pool de N hilos daemon. Los jobs de ClearCut
  (onnxruntime/CPU) sí pueden correr en paralelo.

Ninguno de los dos conoce el dominio de ninguna feature concreta: los
handlers se inyectan desde afuera (ver `api/registry.py` en una fase
posterior), así que agregar un tipo de job nuevo no requiere tocar esta
clase.
"""

from __future__ import annotations

import abc
import asyncio
import logging
import os
import threading
from typing import Any, Callable

from designfabric.jobs.errors import JobCancelled
from designfabric.jobs.models import Job, JobStatus, JobType
from designfabric.jobs.queue import JobQueue
from designfabric.jobs.store import JobStore
from designfabric.jobs.ws_reporter import ProgressHub, WebSocketProgressReporter

logger = logging.getLogger(__name__)

# Un handler ejecuta el trabajo real de un tipo de job y devuelve su resultado
# (o levanta una excepción). No sabe nada de HTTP/pydantic: recibe el payload
# crudo del Job y un reporter de progreso ya listo para usar.
JobHandler = Callable[[Any, WebSocketProgressReporter], Any]


class JobWorker(abc.ABC):
    """Consume una `JobQueue` y ejecuta cada job con el handler registrado para su tipo.

    No conoce el dominio de ninguna feature concreta: los handlers se inyectan
    desde afuera (ver `api/registry.py` en una fase posterior), así que agregar
    un tipo de job nuevo no requiere tocar esta clase.
    """

    def __init__(
        self,
        store: JobStore,
        job_queue: JobQueue,
        hub: ProgressHub,
        handlers: dict[JobType, JobHandler],
    ) -> None:
        self._store = store
        self._queue = job_queue
        self._hub = hub
        self._handlers = handlers
        self._loop: asyncio.AbstractEventLoop | None = None

    def start(self, loop: asyncio.AbstractEventLoop) -> None:
        """Arranca el/los hilo(s) del worker, ligados al event loop de FastAPI
        para publicar progreso."""
        self._loop = loop
        self._spawn_threads()

    @abc.abstractmethod
    def _spawn_threads(self) -> None:
        """Arranca el/los hilo(s) daemon que consumen la cola (política de concurrencia)."""

    def _run_forever(self) -> None:
        while True:
            job_id = self._queue.dequeue_blocking()
            self._process(job_id)

    def _process(self, job_id: str) -> None:
        job = self._store.get(job_id)
        if job is None or job.status is not JobStatus.QUEUED:
            logger.info("Job %s se descarta (cancelado antes de ser tomado por el worker)", job_id)
            return

        handler = self._handlers.get(job.type)
        if handler is None:
            logger.error("Job %s tiene tipo %s sin handler registrado", job_id, job.type.value)
            self._store.mark_failed(job_id, f"No hay handler registrado para {job.type.value}")
            return

        logger.info("Job %s (%s) iniciado", job_id, job.type.value)
        self._store.mark_running(job_id)
        assert self._loop is not None
        reporter = WebSocketProgressReporter(job_id, self._hub, self._loop)

        try:
            result = handler(job.payload, reporter)
            if self._store.is_cancel_requested(job_id):
                self._store.mark_cancelled_running(job_id, result)
                logger.info("Job %s cancelado tras completar el handler", job_id)
                return
            self._store.mark_succeeded(job_id, result)
            logger.info("Job %s completado", job_id)
        except JobCancelled as exc:
            self._store.mark_cancelled_running(job_id, exc.partial_result)
            logger.info("Job %s cancelado (cooperativo)", job_id)
        except Exception as e:
            logger.exception("Job %s falló", job_id)
            self._store.mark_failed(job_id, str(e))


class GpuJobWorker(JobWorker):
    """Un solo hilo daemon: Ollama y FLUX.2 comparten VRAM y no pueden correr en paralelo."""

    def _spawn_threads(self) -> None:
        threading.Thread(target=self._run_forever, daemon=True, name="gpu-job-worker").start()


class CpuJobWorker(JobWorker):
    """Pool de N hilos daemon: los jobs de ClearCut (onnxruntime/CPU) sí pueden correr en paralelo."""

    def __init__(
        self,
        store: JobStore,
        job_queue: JobQueue,
        hub: ProgressHub,
        handlers: dict[JobType, JobHandler],
        max_workers: int | None = None,
    ) -> None:
        super().__init__(store, job_queue, hub, handlers)
        self._max_workers = max_workers or max(1, (os.cpu_count() or 2) - 1)

    def _spawn_threads(self) -> None:
        for i in range(self._max_workers):
            threading.Thread(target=self._run_forever, daemon=True, name=f"cpu-job-worker-{i}").start()
