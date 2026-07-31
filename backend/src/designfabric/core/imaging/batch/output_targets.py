"""Estrategias de salida para el procesamiento por lotes."""

from __future__ import annotations

import zipfile
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

OutputTargetKind = Literal["directory", "zip"]


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


@dataclass(slots=True)
class ZipOutputTarget(OutputTarget):
    """Escribe todos los resultados en un único archivo `.zip`, con una subcarpeta por
    imagen de origen (misma convención de desambiguación que `DirectoryOutputTarget`)."""

    zip_path: Path
    _used_names: set[str] = field(default_factory=set, init=False, repr=False)
    _subfolders: dict[Path, str] = field(default_factory=dict, init=False, repr=False)
    _archive: zipfile.ZipFile | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self.zip_path = Path(self.zip_path)
        self.zip_path.parent.mkdir(parents=True, exist_ok=True)
        self._archive = zipfile.ZipFile(self.zip_path, "w", zipfile.ZIP_DEFLATED)

    def resolve(self, input_path: Path) -> Path:
        """Devuelve la subcarpeta (dentro del zip) asignada a esta imagen de origen. Llamadas
        repetidas con el mismo `input_path` siempre devuelven la misma subcarpeta."""
        key = Path(input_path)
        cached = self._subfolders.get(key)
        if cached is not None:
            return Path(cached)

        stem = key.stem
        candidate = stem
        if candidate not in self._used_names:
            self._used_names.add(candidate)
            self._subfolders[key] = candidate
            return Path(candidate)

        index = 2
        while True:
            candidate = f"{stem}_{index}"
            if candidate not in self._used_names:
                self._used_names.add(candidate)
                self._subfolders[key] = candidate
                return Path(candidate)
            index += 1

    def write(self, subfolder: Path, filename: str, data: bytes) -> str:
        """Agrega `data` al archivo como `<subfolder>/<filename>` y devuelve la ruta interna."""
        if self._archive is None:
            raise RuntimeError("ZipOutputTarget ya fue cerrado.")
        member = f"{subfolder.as_posix()}/{filename}"
        self._archive.writestr(member, data)
        return member

    def close(self) -> None:
        if self._archive is not None:
            self._archive.close()
            self._archive = None

    def __enter__(self) -> "ZipOutputTarget":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()


def create_output_target(
    kind: OutputTargetKind,
    *,
    directory: Path | None = None,
    zip_path: Path | None = None,
) -> OutputTarget:
    """Factory de destinos de salida."""
    if kind == "directory":
        if directory is None:
            raise ValueError("directory es obligatorio para el destino 'directory'.")
        return DirectoryOutputTarget(directory=Path(directory))
    if kind == "zip":
        if zip_path is None:
            raise ValueError("zip_path es obligatorio para el destino 'zip'.")
        return ZipOutputTarget(zip_path=Path(zip_path))
    raise ValueError(f"Destino de salida desconocido: {kind!r}")
