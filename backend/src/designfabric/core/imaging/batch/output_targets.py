"""Estrategias de salida para el procesamiento por lotes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

OutputTargetKind = Literal["directory"]


class OutputTarget(ABC):
    """Resuelve la ruta de salida para un archivo de entrada."""

    @abstractmethod
    def resolve(self, input_path: Path) -> Path:
        """Devuelve la ruta PNG de salida asociada al input."""


@dataclass(slots=True)
class DirectoryOutputTarget(OutputTarget):
    """Escribe todos los resultados en una carpeta plana."""

    directory: Path
    _used_names: set[str] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        self.directory = Path(self.directory)

    def resolve(self, input_path: Path) -> Path:
        stem = Path(input_path).stem
        candidate = f"{stem}.png"
        if candidate not in self._used_names:
            self._used_names.add(candidate)
            return self.directory / candidate

        index = 2
        while True:
            candidate = f"{stem}_{index}.png"
            if candidate not in self._used_names:
                self._used_names.add(candidate)
                return self.directory / candidate
            index += 1


def create_output_target(
    kind: OutputTargetKind,
    *,
    directory: Path | None = None,
) -> OutputTarget:
    """Factory de destinos de salida."""
    if kind == "directory":
        if directory is None:
            raise ValueError("directory es obligatorio para el destino 'directory'.")
        return DirectoryOutputTarget(directory=Path(directory))
    raise ValueError(f"Destino de salida desconocido: {kind!r}")
