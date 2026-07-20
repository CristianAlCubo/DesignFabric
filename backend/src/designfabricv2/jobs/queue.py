"""Cola FIFO thread-safe de ids de jobs pendientes de ejecutar."""

from __future__ import annotations

import queue


class JobQueue:
    """Wrapper tipado sobre `queue.Queue`: garantiza orden FIFO de ejecución de jobs."""

    def __init__(self) -> None:
        self._queue: queue.Queue[str] = queue.Queue()

    def enqueue(self, job_id: str) -> None:
        self._queue.put(job_id)

    def dequeue_blocking(self) -> str:
        """Bloquea el hilo llamante hasta que haya un job disponible."""
        return self._queue.get()
