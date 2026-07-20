"""Facade que oculta a los routers cuál worker/cola usar para cada tipo de job.

NOTA de diseño: este módulo deliberadamente NO importa `api/registry.py`
(que sí importa los routers). Los routers importan `api/dependencies.py`
para declarar `Depends(get_job_dispatcher)`, y `dependencies.py` importa
este módulo — si `dispatcher.py` importara `registry.py` (que a su vez
importa los routers) se cerraría un ciclo:
`dependencies -> dispatcher -> registry -> routers -> dependencies`.
Por eso la afinidad `JobType -> "gpu"/"cpu"` se recibe ya armada en el
constructor: quien la arma (`app.py`, que sí puede importar `registry.py`
sin ciclos) es el único punto que conoce `FEATURE_REGISTRY`.
"""

from __future__ import annotations

from designfabricv2.jobs.models import Job, JobType
from designfabricv2.jobs.queue import JobQueue
from designfabricv2.jobs.store import JobStore


class JobDispatcher:
    """Encola un `Job` en la cola correcta (gpu/cpu) según su tipo, sin que el router lo sepa."""

    def __init__(
        self,
        store: JobStore,
        gpu_queue: JobQueue,
        cpu_queue: JobQueue,
        affinity_by_type: dict[JobType, str],
    ) -> None:
        self._store = store
        self._queues = {"gpu": gpu_queue, "cpu": cpu_queue}
        self._affinity_by_type = affinity_by_type

    def submit(self, job: Job) -> None:
        """Registra el job en el store y lo encola en la cola de su afinidad."""
        self._store.add(job)
        affinity = self._affinity_by_type[job.type]
        self._queues[affinity].enqueue(job.id)
