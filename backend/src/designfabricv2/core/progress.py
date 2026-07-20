"""Abstracción de progreso del dominio (patrón Observer).

El core de generación (`prompt_generator.py`, `sticker_generator.py`) no
sabe renderizar nada: solo emite `ProgressEvent`s a través de un
`ProgressReporter`. Cada adaptador (CLI con `rich`, API con WebSocket)
implementa su propio receptor sin que el dominio dependa de ellos.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Protocol


class ProgressEventType(str, Enum):
    """Tipo de evento dentro del ciclo de vida de una fase del pipeline."""

    STARTED = "started"
    PROGRESS = "progress"
    COMPLETED = "completed"
    FAILED = "failed"
    WARNING = "warning"


class Phase(str, Enum):
    """Fases conocidas del pipeline de generación."""

    PROMPT_GENERATION = "prompt_generation"
    IMAGE_GENERATION = "image_generation"
    CLEARCUT_BATCH = "clearcut_batch"


@dataclass(frozen=True, slots=True)
class ProgressEvent:
    """Evento inmutable de progreso emitido por el dominio.

    `current`/`total` solo tienen sentido para eventos `PROGRESS`/`STARTED`.
    `detail` es texto libre (ej. el concepto o el nombre de archivo actual)
    útil para mostrarlo en la UI sin que el dominio conozca cómo se renderiza.
    """

    phase: Phase
    type: ProgressEventType
    current: int | None = None
    total: int | None = None
    detail: str | None = None
    message: str | None = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class ProgressReporter(Protocol):
    """Puerto que el dominio usa para reportar progreso.

    Cualquier objeto con un método `emit(event)` cumple este protocolo
    (duck typing) — no se requiere heredar de una clase base.
    """

    def emit(self, event: ProgressEvent) -> None: ...


class NullProgressReporter:
    """Implementación no-op: default seguro para uso programático o tests."""

    def emit(self, event: ProgressEvent) -> None:  # noqa: D401 - trivial
        pass


def emit_phase_started(reporter: ProgressReporter, phase: Phase, total: int | None = None) -> None:
    """Notifica el inicio de una fase del pipeline."""
    reporter.emit(ProgressEvent(phase=phase, type=ProgressEventType.STARTED, total=total))


def emit_phase_progress(
    reporter: ProgressReporter, phase: Phase, current: int, total: int, detail: str | None = None
) -> None:
    """Notifica un avance dentro de una fase (ej. concepto/imagen N de total)."""
    reporter.emit(
        ProgressEvent(phase=phase, type=ProgressEventType.PROGRESS, current=current, total=total, detail=detail)
    )


def emit_phase_completed(reporter: ProgressReporter, phase: Phase) -> None:
    """Notifica que una fase terminó exitosamente."""
    reporter.emit(ProgressEvent(phase=phase, type=ProgressEventType.COMPLETED))


def emit_phase_failed(reporter: ProgressReporter, phase: Phase, message: str) -> None:
    """Notifica que una fase falló con un error no recuperable."""
    reporter.emit(ProgressEvent(phase=phase, type=ProgressEventType.FAILED, message=message))


def emit_warning(reporter: ProgressReporter, phase: Phase, message: str) -> None:
    """Notifica un aviso no fatal (ej. un reintento fallido) dentro de una fase."""
    reporter.emit(ProgressEvent(phase=phase, type=ProgressEventType.WARNING, message=message))
