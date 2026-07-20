"""WebSocket de streaming de progreso para un job (genérico, copiado tal cual de DesignFabric)."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/api/jobs", tags=["progress"])


@router.websocket("/{job_id}/ws")
async def job_progress_ws(job_id: str, websocket: WebSocket) -> None:
    """Stream de `ProgressEventSchema` en JSON mientras el job `job_id` corre.

    No se espera ningún mensaje del cliente: el socket se mantiene abierto
    hasta que el cliente se desconecta o el servidor lo cierra.
    """
    hub = websocket.app.state.progress_hub
    await websocket.accept()
    hub.subscribe(job_id, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        hub.unsubscribe(job_id, websocket)
