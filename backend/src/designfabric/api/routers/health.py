"""Healthcheck usado por el proceso main de Electron para saber cuándo el backend está listo."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
