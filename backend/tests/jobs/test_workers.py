"""Tests de `jobs/worker.py`: políticas de concurrencia (GPU serie / CPU paralelo),
manejo de jobs sin handler y de jobs exitosos.

Usamos un event loop real de asyncio corriendo en su propio hilo (en vez de
un test async con pytest-asyncio) porque queremos simular exactamente el
escenario de producción: el worker corre en hilo(s) daemon separados del
loop de FastAPI, y `WebSocketProgressReporter.emit` cruza hacia ese loop con
`asyncio.run_coroutine_threadsafe`. Un solo patrón de "loop en hilo aparte +
polling con timeout sobre el store" se usa en todos los tests para
mantenerlo consistente.
"""

from __future__ import annotations

import threading
import time
from typing import Any

import pytest

from designfabricv2.jobs.models import Job, JobStatus, JobType
from designfabricv2.jobs.queue import JobQueue
from designfabricv2.jobs.store import JobStore
from designfabricv2.jobs.worker import CpuJobWorker, GpuJobWorker
from designfabricv2.jobs.ws_reporter import ProgressHub, WebSocketProgressReporter

POLL_TIMEOUT = 5.0
POLL_INTERVAL = 0.02


@pytest.fixture
def event_loop_in_thread():
    """Levanta un event loop real en un hilo aparte, tal como lo haría FastAPI
    en su propio proceso. Se cierra al final del test."""
    import asyncio

    loop = asyncio.new_event_loop()
    thread = threading.Thread(target=loop.run_forever, daemon=True)
    thread.start()
    yield loop
    loop.call_soon_threadsafe(loop.stop)
    thread.join(timeout=2)
    loop.close()


def _wait_until(predicate, timeout: float = POLL_TIMEOUT) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(POLL_INTERVAL)
    return predicate()


def _wait_for_terminal_status(store: JobStore, job_id: str, timeout: float = POLL_TIMEOUT) -> Job:
    terminal = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
    _wait_until(lambda: store.get(job_id) is not None and store.get(job_id).status in terminal, timeout)
    job = store.get(job_id)
    assert job is not None
    return job


class _ConcurrencyProbe:
    """Handler dummy que registra cuántas ejecuciones están "en curso" a la vez."""

    def __init__(self, sleep_seconds: float = 0.1) -> None:
        self._sleep_seconds = sleep_seconds
        self._lock = threading.Lock()
        self._in_flight = 0
        self.max_in_flight = 0

    def __call__(self, payload: Any, reporter: WebSocketProgressReporter) -> str:
        with self._lock:
            self._in_flight += 1
            self.max_in_flight = max(self.max_in_flight, self._in_flight)
        time.sleep(self._sleep_seconds)
        with self._lock:
            self._in_flight -= 1
        return f"done:{payload}"


def test_gpu_worker_processes_jobs_serially(event_loop_in_thread):
    store = JobStore()
    job_queue = JobQueue()
    hub = ProgressHub()
    probe = _ConcurrencyProbe(sleep_seconds=0.15)
    handlers = {JobType.SINGLE_IMAGE: probe}

    worker = GpuJobWorker(store, job_queue, hub, handlers)
    worker.start(event_loop_in_thread)

    jobs = [Job.new(JobType.SINGLE_IMAGE, payload=f"p{i}") for i in range(3)]
    for job in jobs:
        store.add(job)
        job_queue.enqueue(job.id)

    for job in jobs:
        finished = _wait_for_terminal_status(store, job.id)
        assert finished.status is JobStatus.SUCCEEDED

    # Si dos jobs se hubieran solapado, max_in_flight sería >= 2: el worker
    # de GPU debe garantizar que nunca haya más de un job corriendo a la vez.
    assert probe.max_in_flight == 1


def test_cpu_worker_processes_jobs_in_parallel(event_loop_in_thread):
    store = JobStore()
    job_queue = JobQueue()
    hub = ProgressHub()
    probe = _ConcurrencyProbe(sleep_seconds=0.2)
    handlers = {JobType.CLEARCUT_BATCH: probe}

    worker = CpuJobWorker(store, job_queue, hub, handlers, max_workers=3)
    worker.start(event_loop_in_thread)

    jobs = [Job.new(JobType.CLEARCUT_BATCH, payload=f"p{i}") for i in range(3)]
    for job in jobs:
        store.add(job)
        job_queue.enqueue(job.id)

    for job in jobs:
        finished = _wait_for_terminal_status(store, job.id)
        assert finished.status is JobStatus.SUCCEEDED

    # Con 3 hilos disponibles y 3 jobs que duermen simultáneamente, en algún
    # momento debieron solaparse.
    assert probe.max_in_flight > 1


def test_job_with_unregistered_type_fails_gracefully(event_loop_in_thread):
    store = JobStore()
    job_queue = JobQueue()
    hub = ProgressHub()
    handlers: dict[JobType, Any] = {}  # sin handlers registrados

    worker = GpuJobWorker(store, job_queue, hub, handlers)
    worker.start(event_loop_in_thread)

    job = Job.new(JobType.SCALE, payload={})
    store.add(job)
    job_queue.enqueue(job.id)

    finished = _wait_for_terminal_status(store, job.id)
    assert finished.status is JobStatus.FAILED
    assert finished.error is not None
    assert "scale" in finished.error.lower() or JobType.SCALE.value in finished.error


def test_successful_job_stores_handler_result(event_loop_in_thread):
    store = JobStore()
    job_queue = JobQueue()
    hub = ProgressHub()

    def handler(payload: Any, reporter: WebSocketProgressReporter) -> dict:
        return {"echo": payload}

    worker = GpuJobWorker(store, job_queue, hub, {JobType.BATCH: handler})
    worker.start(event_loop_in_thread)

    job = Job.new(JobType.BATCH, payload="hello")
    store.add(job)
    job_queue.enqueue(job.id)

    finished = _wait_for_terminal_status(store, job.id)
    assert finished.status is JobStatus.SUCCEEDED
    assert finished.result == {"echo": "hello"}
    assert finished.error is None


def test_failing_handler_marks_job_failed(event_loop_in_thread):
    store = JobStore()
    job_queue = JobQueue()
    hub = ProgressHub()

    def handler(payload: Any, reporter: WebSocketProgressReporter) -> Any:
        raise ValueError("algo salió mal")

    worker = GpuJobWorker(store, job_queue, hub, {JobType.BATCH: handler})
    worker.start(event_loop_in_thread)

    job = Job.new(JobType.BATCH, payload="x")
    store.add(job)
    job_queue.enqueue(job.id)

    finished = _wait_for_terminal_status(store, job.id)
    assert finished.status is JobStatus.FAILED
    assert finished.error == "algo salió mal"
