"""Estrategias de entrada para el procesamiento por lotes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from designfabric.core.imaging.background_remover import SUPPORTED_EXTENSIONS

InputSourceKind = Literal["folder", "files"]


def is_supported_image(path: Path) -> bool:
    """Indica si la extensión es válida para el pipeline de recorte."""
    return path.suffix.lower() in SUPPORTED_EXTENSIONS


class InputSource(ABC):
    """Resuelve la lista de rutas candidatas a procesar."""

    @abstractmethod
    def resolve(self) -> list[Path]:
        """Devuelve rutas de archivo (pueden incluir no soportadas)."""


@dataclass(frozen=True, slots=True)
class FolderInputSource(InputSource):
    """Lista archivos de una carpeta sin recursión."""

    directory: Path

    def resolve(self) -> list[Path]:
        directory = Path(self.directory)
        if not directory.is_dir():
            raise FileNotFoundError(f"No existe la carpeta de entrada: {directory}")

        entries = [
            path
            for path in sorted(directory.iterdir(), key=lambda p: p.name.lower())
            if path.is_file()
        ]
        return entries


@dataclass(frozen=True, slots=True)
class FilesInputSource(InputSource):
    """Usa exactamente la lista de archivos indicada por el usuario."""

    paths: tuple[Path, ...]

    def resolve(self) -> list[Path]:
        if not self.paths:
            raise ValueError("La lista de archivos de entrada está vacía.")
        return [Path(path) for path in self.paths]


def create_input_source(
    kind: InputSourceKind,
    *,
    directory: Path | None = None,
    paths: list[Path] | tuple[Path, ...] | None = None,
) -> InputSource:
    """Factory de fuentes de entrada."""
    if kind == "folder":
        if directory is None:
            raise ValueError("directory es obligatorio para la fuente 'folder'.")
        return FolderInputSource(directory=Path(directory))
    if kind == "files":
        if paths is None:
            raise ValueError("paths es obligatorio para la fuente 'files'.")
        return FilesInputSource(paths=tuple(Path(path) for path in paths))
    raise ValueError(f"Fuente de entrada desconocida: {kind!r}")
