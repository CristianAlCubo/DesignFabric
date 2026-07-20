"""Resultados y helpers de generación de imagen; facade fina hacia ImageProvider.

La lógica del motor FLUX vive en `image_providers.FluxImageProvider`.
Este módulo conserva `StickerResult`/`slugify`/`generate_stickers` como
superficie estable para tests y serialización.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from designfabric.core.progress import NullProgressReporter, ProgressReporter


@dataclass(frozen=True, slots=True)
class StickerResult:
    """Resultado técnico de generar una imagen a partir de un prompt."""

    prompt: str
    filename: str | None
    success: bool
    error: str | None = None


def slugify(text: str, max_len: int = 40) -> str:
    """Convierte texto libre en un slug apto para nombre de archivo."""
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug[:max_len]


def generate_stickers(
    prompts: list[str],
    output_dir: str = "output",
    reporter: ProgressReporter = NullProgressReporter(),
) -> list[StickerResult]:
    """Compat: genera stickers con el provider Flux por defecto."""
    from designfabric.core.generation.image_providers import FluxImageProvider

    return FluxImageProvider().generate_images(prompts, output_dir=output_dir, reporter=reporter)
