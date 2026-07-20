"""Streaming de progreso vía WebSocket.

`ProgressHub` hace de registro de suscriptores por job (fan-out).
`WebSocketProgressReporter` es el adaptador de `ProgressReporter` para la
API: traduce `ProgressEvent`s de dominio a mensajes JSON publicados en el
hub. El pipeline corre en el hilo de un `JobWorker` (GPU o CPU), no en el
event loop de FastAPI, así que `emit` debe cruzar hacia el loop async
explícitamente.
"""

from __future__ import annotations

import asyncio
import logging
import threading

from fastapi import WebSocket

from designfabric.api.schemas import ProgressEventSchema
from designfabric.core.progress import ProgressEvent, ProgressEventType

logger = logging.getLogger(__name__)


class ProgressHub:
    """Registro de WebSockets suscritos a cada job, para publicar eventos por fan-out."""

    def __init__(self) -> None:
        self._connections: dict[str, list[WebSocket]] = {}
        self._lock = threading.Lock()

    def subscribe(self, job_id: str, websocket: WebSocket) -> None:
        with self._lock:
            self._connections.setdefault(job_id, []).append(websocket)

    def unsubscribe(self, job_id: str, websocket: WebSocket) -> None:
        with self._lock:
            connections = self._connections.get(job_id, [])
            if websocket in connections:
                connections.remove(websocket)

    async def publish(self, job_id: str, payload: dict) -> None:
        """Envía `payload` a todos los sockets suscritos a `job_id`, descartando los caídos."""
        with self._lock:
            connections = list(self._connections.get(job_id, []))
        for websocket in connections:
            try:
                await websocket.send_json(payload)
            except Exception:
                self.unsubscribe(job_id, websocket)


class WebSocketProgressReporter:
    """Adaptador de `ProgressReporter` que publica eventos en un `ProgressHub`.

    Se instancia una vez por job, ligada al event loop de FastAPI que estaba
    corriendo cuando se creó el worker (capturado en `loop`).
    """

    def __init__(self, job_id: str, hub: ProgressHub, loop: asyncio.AbstractEventLoop) -> None:
        self._job_id = job_id
        self._hub = hub
        self._loop = loop

    def emit(self, event: ProgressEvent) -> None:
        # Además de publicarse en el WS del job, warnings y fallos quedan en
        # el log general (stdout) — visibles en la consola de observabilidad
        # aunque nadie tenga ese job abierto en la UI en ese momento.
        if event.type is ProgressEventType.WARNING:
            logger.warning("[job %s] %s", self._job_id, event.message)
        elif event.type is ProgressEventType.FAILED:
            logger.error("[job %s] %s: %s", self._job_id, event.phase.value, event.message)

        schema = ProgressEventSchema(
            job_id=self._job_id,
            phase=event.phase.value,
            type=event.type.value,
            current=event.current,
            total=event.total,
            detail=event.detail,
            message=event.message,
            timestamp=event.timestamp,
        )
        # `emit` se llama desde el hilo del worker (síncrono); despachamos la
        # publicación al event loop async de forma thread-safe.
        asyncio.run_coroutine_threadsafe(
            self._hub.publish(self._job_id, schema.model_dump(mode="json")),
            self._loop,
        )
