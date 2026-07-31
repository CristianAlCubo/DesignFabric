"""Pipeline de exportación multi-tamaño: redimensiona cada imagen de entrada contra cada
fila de tamaño de un preset (fijo en px o porcentual) y empaqueta todos los resultados en un
único `.zip`, tolerando fallos parciales por combinación imagen/tamaño."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import cv2
import numpy as np

from designfabric.core.imaging.ai_upscalers.common import (
    encode_png_bgra,
    resize_bgra,
    resolve_percent_size,
    resolve_target_size,
)
from designfabric.core.imaging.background_remover import SUPPORTED_EXTENSIONS
from designfabric.core.imaging.batch.output_targets import ZipOutputTarget
from designfabric.core.progress import (
    Phase,
    ProgressReporter,
    emit_phase_completed,
    emit_phase_progress,
    emit_phase_started,
    emit_warning,
)

logger = logging.getLogger(__name__)

SizeMode = Literal["px", "percent"]
ItemStatus = Literal["succeeded", "failed"]

DEFAULT_TEMPLATE = "{prefix}{name}"


@dataclass(frozen=True, slots=True)
class SizeRow:
    """Una fila de un preset: un tamaño destino + cómo nombrar el archivo resultante."""

    label: str
    mode: SizeMode
    prefix: str = ""
    width: int | None = None
    height: int | None = None
    percent: float | None = None
    template: str | None = None


@dataclass(frozen=True, slots=True)
class MultiExportItemResult:
    """Resultado de exportar una combinación (imagen, fila de tamaño)."""

    input_path: Path
    size_label: str
    status: ItemStatus
    archive_member: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "input": str(self.input_path),
            "size_label": self.size_label,
            "status": self.status,
            "archive_member": self.archive_member,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class MultiExportReport:
    """Resumen agregado de la corrida completa."""

    zip_path: Path
    items: tuple[MultiExportItemResult, ...]

    @property
    def expected(self) -> int:
        return len(self.items)

    @property
    def produced(self) -> int:
        return sum(1 for item in self.items if item.status == "succeeded")

    def to_dict(self) -> dict[str, object]:
        return {
            "zip_path": str(self.zip_path),
            "expected": self.expected,
            "produced": self.produced,
            "items": [item.to_dict() for item in self.items],
        }


def _format_percent(percent: float | None) -> str:
    if percent is None:
        return ""
    return str(int(percent)) if float(percent).is_integer() else str(percent)


def render_filename(row: SizeRow, *, stem: str, width: int, height: int) -> str:
    """Renderiza el nombre de archivo (sin extensión) de una fila para una imagen dada."""
    template = row.template or DEFAULT_TEMPLATE
    name = template.format(
        name=stem,
        width=width,
        height=height,
        percent=_format_percent(row.percent),
        prefix=row.prefix,
    )
    return f"{name}.png"


def _load_bgra(path: Path) -> np.ndarray:
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Formato no soportado '{path.suffix}'. Formatos soportados: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    image = cv2.imread(str(path), cv2.IMREAD_UNCHANGED)
    if image is None:
        raise ValueError(f"No se pudo leer la imagen: {path}")
    if image.ndim == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2BGRA)
    if image.shape[2] == 3:
        return cv2.cvtColor(image, cv2.COLOR_BGR2BGRA)
    return image


def _resolve_size(row: SizeRow, src_width: int, src_height: int) -> tuple[int, int]:
    if row.mode == "percent":
        return resolve_percent_size(src_width, src_height, row.percent if row.percent is not None else 100.0)
    return resolve_target_size(src_width, src_height, row.width, row.height)


def run_multi_export(
    image_paths: list[Path],
    sizes: list[SizeRow],
    zip_path: Path,
    *,
    reporter: ProgressReporter | None = None,
) -> MultiExportReport:
    """Ejecuta la exportación multi-tamaño y devuelve el reporte agregado.

    Un fallo al leer una imagen o al redimensionar una fila puntual no aborta el resto del
    trabajo: se registra como ítem fallido y la corrida continúa.
    """
    total = len(image_paths) * len(sizes)
    items: list[MultiExportItemResult] = []
    target = ZipOutputTarget(zip_path=zip_path)
    done = 0

    if reporter is not None:
        emit_phase_started(reporter, Phase.MULTI_EXPORT, total=total)

    try:
        for input_path in image_paths:
            subfolder = target.resolve(input_path)

            try:
                source = _load_bgra(input_path)
            except Exception as exc:  # noqa: BLE001 — un fallo de lectura no aborta el lote
                logger.warning("Fallo al leer %s: %s", input_path, exc)
                for row in sizes:
                    items.append(
                        MultiExportItemResult(
                            input_path=input_path,
                            size_label=row.label,
                            status="failed",
                            error=str(exc),
                        )
                    )
                    done += 1
                    if reporter is not None:
                        emit_phase_progress(reporter, Phase.MULTI_EXPORT, done, total, detail=str(input_path))
                if reporter is not None:
                    emit_warning(reporter, Phase.MULTI_EXPORT, str(exc))
                continue

            src_h, src_w = source.shape[:2]
            for row in sizes:
                try:
                    width, height = _resolve_size(row, src_w, src_h)
                    resized = resize_bgra(source, width, height)
                    filename = render_filename(row, stem=input_path.stem, width=width, height=height)
                    member = target.write(subfolder, filename, encode_png_bgra(resized))
                    items.append(
                        MultiExportItemResult(
                            input_path=input_path,
                            size_label=row.label,
                            status="succeeded",
                            archive_member=member,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 — un tamaño fallido no aborta el resto
                    logger.warning("Fallo al exportar %s @ %s: %s", input_path, row.label, exc)
                    items.append(
                        MultiExportItemResult(
                            input_path=input_path,
                            size_label=row.label,
                            status="failed",
                            error=str(exc),
                        )
                    )
                    if reporter is not None:
                        emit_warning(reporter, Phase.MULTI_EXPORT, str(exc))

                done += 1
                if reporter is not None:
                    emit_phase_progress(reporter, Phase.MULTI_EXPORT, done, total, detail=str(input_path))
    finally:
        target.close()

    if reporter is not None:
        emit_phase_completed(reporter, Phase.MULTI_EXPORT)

    return MultiExportReport(zip_path=zip_path, items=tuple(items))


__all__ = [
    "DEFAULT_TEMPLATE",
    "MultiExportItemResult",
    "MultiExportReport",
    "SizeRow",
    "render_filename",
    "run_multi_export",
]
