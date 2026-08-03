"""Pipeline de conversión de formato de imágenes con Pillow.

Convierte una imagen (o un lote) entre JPEG/JPG/PNG/WEBP. `JPG` y `JPEG` son el
mismo codec de Pillow (`"JPEG"`), diferenciados solo por la extensión de salida.
Al convertir a JPEG —que no soporta canal alpha— la transparencia se aplana sobre
un fondo blanco. En modo lote, un fallo puntual no aborta el resto: se registra
como ítem fallido y la corrida continúa, empaquetando lo producido en un `.zip`.
"""

from __future__ import annotations

import logging
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Literal

from PIL import Image

from designfabric.core.progress import (
    Phase,
    ProgressReporter,
    emit_phase_completed,
    emit_phase_progress,
    emit_phase_started,
    emit_warning,
)

logger = logging.getLogger(__name__)

TargetFormat = Literal["JPEG", "JPG", "PNG", "WEBP"]
ItemStatus = Literal["succeeded", "failed"]

DEFAULT_QUALITY = 90
WHITE = (255, 255, 255)


@dataclass(frozen=True, slots=True)
class FormatSpec:
    """Cómo guardar en un formato destino: codec Pillow, extensión y capacidades."""

    pillow_format: str
    extension: str
    supports_quality: bool
    supports_alpha: bool


# `JPG` y `JPEG` comparten codec `"JPEG"`; se estandariza la extensión a `.jpg`.
_FORMATS: dict[str, FormatSpec] = {
    "JPEG": FormatSpec("JPEG", ".jpg", supports_quality=True, supports_alpha=False),
    "JPG": FormatSpec("JPEG", ".jpg", supports_quality=True, supports_alpha=False),
    "PNG": FormatSpec("PNG", ".png", supports_quality=False, supports_alpha=True),
    "WEBP": FormatSpec("WEBP", ".webp", supports_quality=True, supports_alpha=True),
}


def resolve_target_format(target_format: str) -> FormatSpec:
    """Devuelve el `FormatSpec` del formato destino (case-insensitive)."""
    spec = _FORMATS.get(target_format.upper())
    if spec is None:
        raise ValueError(
            f"Formato destino no soportado '{target_format}'. Soportados: {sorted(_FORMATS)}"
        )
    return spec


def _clamp_quality(quality: int) -> int:
    return max(0, min(100, quality))


def _has_alpha(img: Image.Image) -> bool:
    return img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)


def _flatten_to_rgb(img: Image.Image, background: tuple[int, int, int] = WHITE) -> Image.Image:
    """Aplana la transparencia sobre `background` (blanco por defecto) y devuelve RGB.

    Las imágenes sin canal alpha se convierten a RGB directamente, sin introducir
    ningún relleno de fondo.
    """
    if _has_alpha(img):
        rgba = img.convert("RGBA")
        canvas = Image.new("RGB", rgba.size, background)
        canvas.paste(rgba, mask=rgba.split()[-1])
        return canvas
    return img.convert("RGB")


def _prepare_image(img: Image.Image, spec: FormatSpec) -> Image.Image:
    """Normaliza el modo de la imagen para el formato destino."""
    if not spec.supports_alpha:
        # JPEG: sin alpha → aplanar sobre blanco.
        return _flatten_to_rgb(img)
    # PNG/WEBP: preservar transparencia si la hay.
    return img.convert("RGBA") if _has_alpha(img) else img.convert("RGB")


def _save_kwargs(spec: FormatSpec, quality: int, webp_lossless: bool) -> dict[str, object]:
    """Construye los kwargs de `Image.save` según el formato y la calidad pedida."""
    if spec.pillow_format == "PNG":
        return {"optimize": True}
    if spec.pillow_format == "WEBP":
        if webp_lossless:
            return {"lossless": True}
        return {"quality": _clamp_quality(quality)}
    # JPEG
    return {"quality": _clamp_quality(quality), "optimize": True}


def _encode(img: Image.Image, spec: FormatSpec, quality: int, webp_lossless: bool) -> bytes:
    prepared = _prepare_image(img, spec)
    buffer = BytesIO()
    prepared.save(buffer, format=spec.pillow_format, **_save_kwargs(spec, quality, webp_lossless))
    return buffer.getvalue()


def convert_one(
    src: Path,
    dest: Path,
    target_format: TargetFormat | str,
    *,
    quality: int = DEFAULT_QUALITY,
    webp_lossless: bool = False,
) -> Path:
    """Convierte una imagen individual a `dest` en el formato destino.

    Devuelve la ruta escrita (con la extensión propia del formato ya aplicada por
    el llamador). Lanza si la imagen no puede decodificarse o el formato es inválido.
    """
    spec = resolve_target_format(str(target_format))
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(src) as img:
        img.load()
        data = _encode(img, spec, quality, webp_lossless)
    dest.write_bytes(data)
    return dest


@dataclass(frozen=True, slots=True)
class ConvertItemResult:
    """Resultado de convertir una imagen del lote."""

    input_path: Path
    status: ItemStatus
    archive_member: str | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {
            "input": str(self.input_path),
            "status": self.status,
            "archive_member": self.archive_member,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class ConvertBatchReport:
    """Resumen agregado de una conversión en lote."""

    zip_path: Path
    items: tuple[ConvertItemResult, ...]

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


def _unique_member(stem: str, extension: str, used: set[str]) -> str:
    """Nombre plano único dentro del zip: `<stem><ext>`, `<stem>_2<ext>`, …"""
    candidate = f"{stem}{extension}"
    if candidate not in used:
        used.add(candidate)
        return candidate
    index = 2
    while True:
        candidate = f"{stem}_{index}{extension}"
        if candidate not in used:
            used.add(candidate)
            return candidate
        index += 1


def convert_batch(
    image_paths: list[Path],
    target_format: TargetFormat | str,
    zip_path: Path,
    *,
    quality: int = DEFAULT_QUALITY,
    webp_lossless: bool = False,
    reporter: ProgressReporter | None = None,
) -> ConvertBatchReport:
    """Convierte todas las imágenes al mismo formato destino y las empaqueta en un `.zip`.

    Cada imagen conserva su nombre base con la extensión del formato destino; las
    colisiones de nombre se desambiguan con un sufijo `_N`. Un fallo puntual no
    aborta el lote: se registra como ítem fallido y la corrida continúa.
    """
    spec = resolve_target_format(str(target_format))
    total = len(image_paths)
    items: list[ConvertItemResult] = []
    used_names: set[str] = set()
    done = 0

    zip_path.parent.mkdir(parents=True, exist_ok=True)

    if reporter is not None:
        emit_phase_started(reporter, Phase.CONVERT, total=total)

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for input_path in image_paths:
            try:
                with Image.open(input_path) as img:
                    img.load()
                    data = _encode(img, spec, quality, webp_lossless)
                member = _unique_member(input_path.stem, spec.extension, used_names)
                archive.writestr(member, data)
                items.append(
                    ConvertItemResult(input_path=input_path, status="succeeded", archive_member=member)
                )
            except Exception as exc:  # noqa: BLE001 — un fallo puntual no aborta el lote
                logger.warning("Fallo al convertir %s: %s", input_path, exc)
                items.append(ConvertItemResult(input_path=input_path, status="failed", error=str(exc)))
                if reporter is not None:
                    emit_warning(reporter, Phase.CONVERT, str(exc))

            done += 1
            if reporter is not None:
                emit_phase_progress(reporter, Phase.CONVERT, done, total, detail=str(input_path))

    if reporter is not None:
        emit_phase_completed(reporter, Phase.CONVERT)

    return ConvertBatchReport(zip_path=zip_path, items=tuple(items))


__all__ = [
    "DEFAULT_QUALITY",
    "ConvertBatchReport",
    "ConvertItemResult",
    "FormatSpec",
    "TargetFormat",
    "convert_batch",
    "convert_one",
    "resolve_target_format",
]
