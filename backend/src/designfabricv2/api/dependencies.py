"""Dependencias de FastAPI: resuelven los singletons compartidos guardados en `app.state`.

Los routers solo dependen de 3 cosas: el store (para consultar/cancelar
jobs), el dispatcher (para encolar jobs sin saber a qué worker/cola van) y
los settings. `JobQueue`/`ProgressHub` no se exponen como dependencias de
router porque ningún router los necesita directamente (el dispatcher oculta
las colas; el hub solo lo usa `progress_ws.py`, que lo lee de `app.state`
directamente al no depender de tipos de job concretos).
"""

from __future__ import annotations

from fastapi import Request

from designfabricv2.api.dispatcher import JobDispatcher
from designfabricv2.core.config import Settings
from designfabricv2.jobs.store import JobStore


def get_job_store(request: Request) -> JobStore:
    return request.app.state.job_store


def get_job_dispatcher(request: Request) -> JobDispatcher:
    return request.app.state.job_dispatcher


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings
