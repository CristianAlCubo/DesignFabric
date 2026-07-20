"""Renderizado en consola (rich) del progreso del pipeline de generación IA.

`RichProgressReporter` implementa `ProgressReporter` traduciendo los eventos
de dominio a una barra de progreso + mensajes de éxito/fallo. Usado por el
CLI `designfabric` (conservado como herramienta standalone junto al `clearcut`
en esta fusión).
"""

from __future__ import annotations

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from designfabricv2.core.progress import Phase, ProgressEvent, ProgressEventType

console = Console()

# Título, ícono y color de consola asociados a cada fase del pipeline.
_PHASE_STYLE: dict[Phase, tuple[str, str, str]] = {
    Phase.PROMPT_GENERATION: ("Generación de prompts", "🧠", "cyan"),
    Phase.IMAGE_GENERATION: ("Generación de imágenes", "🎨", "magenta"),
}


def _build_progress(color: str) -> Progress:
    """Barra de progreso estándar del proyecto, lista para usarse con `start()`/`stop()`."""
    return Progress(
        SpinnerColumn(style=color),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(complete_style=color, finished_style="bold green"),
        MofNCompleteColumn(),
        TimeElapsedColumn(),
        console=console,
    )


class RichProgressReporter:
    """Adaptador de consola: recibe `ProgressEvent`s y los dibuja con `rich`."""

    def __init__(self) -> None:
        self._progress: Progress | None = None
        self._task_ids: dict[Phase, int] = {}

    def emit(self, event: ProgressEvent) -> None:
        title, icon, color = _PHASE_STYLE[event.phase]

        if event.type is ProgressEventType.STARTED:
            console.rule(f"[bold {color}]{icon}  {title} ({event.total})[/bold {color}]", style=color)
            self._progress = _build_progress(color)
            self._progress.start()
            self._task_ids[event.phase] = self._progress.add_task("Procesando", total=event.total)

        elif event.type is ProgressEventType.PROGRESS:
            assert self._progress is not None
            task_id = self._task_ids[event.phase]
            description = f"[{color}]{event.detail[:50]}" if event.detail else None
            if description:
                self._progress.update(task_id, advance=1, description=description)
            else:
                self._progress.update(task_id, advance=1)

        elif event.type is ProgressEventType.COMPLETED:
            if self._progress is not None:
                self._progress.stop()
            console.print(f"[bold green]✔ {title} completada[/bold green]\n")

        elif event.type is ProgressEventType.FAILED:
            if self._progress is not None:
                self._progress.stop()
            console.print(f"[bold red]✘ {title} falló: {event.message}[/bold red]\n")

        elif event.type is ProgressEventType.WARNING:
            console.print(f"[yellow]Aviso: {event.message}[/yellow]")
