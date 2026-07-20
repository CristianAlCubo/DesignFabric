"""Errores del sistema de jobs."""

from __future__ import annotations

from typing import Any


class JobCancelled(Exception):
    """El handler abortó de forma cooperativa tras una solicitud de cancelación."""

    def __init__(self, message: str = "Job cancelado", *, partial_result: Any | None = None) -> None:
        super().__init__(message)
        self.partial_result = partial_result
